import asyncio
import signal
import sys
from contextlib import suppress

import aiosqlite
import structlog
from aiogram import Bot, Dispatcher

from .core import BotCore
from .dictionary import unpack
from .health import run_health_check_server
from .logging_conf import configure_logging
from .recognition import BaseSpeechRecognizer, get_recognizer_by_name
from .settings import Settings, get_settings
from .telegram import build_bot
from .transcription_cache import (
    BaseTranscriptionCache,
    InMemoryTranscriptionCache,
    NullTranscriptionCache,
    SqliteTranscriptionCache,
)
from .word_count import AhoCorasickWordCounter, BaseWordCounter

logger = structlog.getLogger(__name__)
STOP_SIGNALS = (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)
GRACEFUL_SHUTDOWN_TIMEOUT = 10  # seconds


def load_recognition_core(settings: Settings) -> BaseSpeechRecognizer:
    recognizer_cls = get_recognizer_by_name(settings.recognition.engine)
    logger.info("Loading speech recognition engine...", engine=recognizer_cls.__name__)
    recognizer: BaseSpeechRecognizer = recognizer_cls.from_options(**settings.recognition.engine_options)
    logger.info("Speech recognition engine loaded")
    return recognizer


def load_word_counter(settings: Settings) -> BaseWordCounter:
    logger.info("Loading packed dictionary...", path=str(settings.service.dict_file))
    blob = settings.service.dict_file.read_bytes()
    dictionary = unpack(blob)
    logger.info("Dict loaded", total_entries=len(dictionary))

    logger.info("Assembling automata...")
    return AhoCorasickWordCounter.from_dictionary(dictionary)


async def make_cache(settings: Settings) -> BaseTranscriptionCache:
    cache: BaseTranscriptionCache
    if settings.cache.engine == "memory":
        ttl = settings.cache.params["ttl"]
        cache = InMemoryTranscriptionCache(ttl)
        logger.info("Cache engine loaded", ttl=ttl, engine="InMemoryTranscriptionCache")
    elif settings.cache.engine == "sqlite":
        db_path = settings.cache.params["db_path"]
        ttl = settings.cache.params.get("ttl")
        conn = await aiosqlite.connect(db_path)
        cache = SqliteTranscriptionCache(conn, ttl)
        logger.info("Cache engine loaded", db_path=db_path, ttl=ttl, engine="SqliteTranscriptionCache")
    else:
        cache = NullTranscriptionCache()
        logger.warning("Cache settings not defined, cache disabled")
    return cache


async def periodic_cache_cleanup(
    cache: BaseTranscriptionCache,
    stop_event: asyncio.Event,
    interval_seconds: int,
) -> None:
    """Periodically clean expired cache entries until stop_event is set."""
    logger.info("Starting periodic cache cleanup", interval_seconds=interval_seconds)

    while not stop_event.is_set():
        # Wait for the interval or until stop_event is set
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
            # If we get here, stop_event was set
            break
        except asyncio.TimeoutError:
            # Timeout means we should run cleanup
            pass

        # Perform cleanup
        try:
            deleted_count = await cache.clean()
            if deleted_count > 0:
                logger.info("Periodic cache cleanup completed", deleted=deleted_count)
            else:
                logger.debug("Periodic cache cleanup completed, no expired entries")
        except Exception:
            logger.exception("Error during periodic cache cleanup")

    logger.info("Periodic cache cleanup stopped")


async def run_telegram_polling(
    bot: Bot,
    dispatcher: Dispatcher,
    stop_event: asyncio.Event,
) -> None:
    """Run telegram polling until stop_event is set."""
    # Start polling in a separate task so we can stop it gracefully
    polling_task = asyncio.create_task(
        dispatcher.start_polling(bot, handle_signals=False),
        name="telegram_polling_inner",
    )

    # Wait for stop event
    await stop_event.wait()

    # Stop polling gracefully
    logger.info("Stopping telegram polling...")
    await dispatcher.stop_polling()

    # Wait for the polling task to complete
    with suppress(asyncio.CancelledError):
        await polling_task

    logger.info("Telegram polling stopped")


async def wait_tasks_shutdown(tasks: set[asyncio.Task], stop_event: asyncio.Event) -> None:
    """Wait for tasks to complete and handle graceful shutdown."""
    if not tasks:
        return

    # Wait for any task to complete first (or stop_event)
    stop_wait_task = asyncio.create_task(stop_event.wait(), name="stop_event_waiter")
    all_tasks = tasks | {stop_wait_task}

    finished, pending = await asyncio.wait(all_tasks, return_when=asyncio.FIRST_COMPLETED)

    # Log finished tasks
    for task in finished:
        if task is stop_wait_task:
            continue
        try:
            exc = task.exception()
            if exc:
                logger.exception(f"Task {task.get_name()!r} exited with exception", exc_info=exc)
            else:
                logger.info(f"Task {task.get_name()!r} exited gracefully")
        except asyncio.CancelledError:
            logger.info(f"Task {task.get_name()!r} was cancelled")

    # Remove stop_wait_task from pending if present
    pending.discard(stop_wait_task)
    if not stop_wait_task.done():
        stop_wait_task.cancel()
        with suppress(asyncio.CancelledError):
            await stop_wait_task

    if not pending:
        return

    logger.warning("Starting graceful shutdown", pending_tasks=len(pending))

    # Signal stop to all tasks
    stop_event.set()

    # Wait for graceful shutdown with timeout
    done, still_pending = await asyncio.wait(pending, timeout=GRACEFUL_SHUTDOWN_TIMEOUT)

    for task in done:
        try:
            exc = task.exception()
            if exc:
                logger.exception(f"Task {task.get_name()!r} raised exception during shutdown", exc_info=exc)
            else:
                logger.info(f"Task {task.get_name()!r} exited gracefully")
        except asyncio.CancelledError:
            logger.info(f"Task {task.get_name()!r} was cancelled")

    if still_pending:
        logger.warning("Graceful shutdown timeout exceeded, cancelling remaining tasks", count=len(still_pending))
        for task in still_pending:
            logger.warning(f"Cancelling task {task.get_name()!r}")
            task.cancel()

        await asyncio.gather(*still_pending, return_exceptions=True)

        for task in still_pending:
            if task.cancelled():
                logger.warning(f"Task {task.get_name()!r} was successfully cancelled")
            elif task.exception() is not None:
                logger.exception(f"Task {task.get_name()!r} raised exception during cancellation")

    logger.info("Shutdown complete")


async def _main(stop_event: asyncio.Event) -> None:
    settings = get_settings()

    configure_logging(log_level=settings.service.log_level, console_colors=settings.service.log_colors)
    logger.info("Logging configured", log_level=settings.service.log_level, console_colors=settings.service.log_colors)

    logger.info("Creating bot core...")
    cache = await make_cache(settings)
    await cache.setup()
    bot_core = BotCore(load_recognition_core(settings), load_word_counter(settings), cache=cache)
    logger.info("Bot core assembled")

    # Task registry
    tasks: set[asyncio.Task] = set()

    # Start health check server
    health_task = asyncio.create_task(
        run_health_check_server(
            lambda: True,  # TODO: Implement actual health check
            settings.health_check.host,
            settings.health_check.port,
            settings.health_check.path,
            stop_event,
        ),
        name="health_check",
    )
    tasks.add(health_task)

    # Start periodic cache cleanup if configured
    if settings.cache.periodic_cleanup is not None and settings.cache.engine is not None:
        cleanup_task = asyncio.create_task(
            periodic_cache_cleanup(cache, stop_event, settings.cache.periodic_cleanup),
            name="cache_cleanup",
        )
        tasks.add(cleanup_task)
        logger.info("Periodic cache cleanup routine started", interval_seconds=settings.cache.periodic_cleanup)

    logger.info("Starting bot...")
    token = settings.telegram.bot_token
    logger.info("Using bot token", token=f"{token[:5]}...{token[-5:]}")
    logger.info("Transcribe command", transcribe_command=settings.telegram.transcribe_command)

    bot, dispatcher = build_bot(
        settings.telegram.bot_token,
        bot_core,
        transcribe_command=settings.telegram.transcribe_command,
        service_settings=settings.service,
    )

    # FIXME: aiogram configures logging and overrides our setting, so here we hack it by setting config again.
    configure_logging(log_level=settings.service.log_level, console_colors=settings.service.log_colors)

    # Start telegram polling task (wraps dispatcher with graceful stop)
    polling_task = asyncio.create_task(
        run_telegram_polling(bot, dispatcher, stop_event),
        name="telegram_polling",
    )
    tasks.add(polling_task)

    logger.info("Service ready")

    # Wait for shutdown
    await wait_tasks_shutdown(tasks, stop_event)

    # Cleanup resources
    try:
        await cache.teardown()
    except Exception:
        logger.exception("Error during cache teardown")

    logger.info("Bye!")


def main() -> None:
    loop = asyncio.new_event_loop()
    stop_event = asyncio.Event()

    def stop_all() -> None:
        stop_event.set()
        logger.warning("Shutting down service! Press ^C again to terminate")

        def terminate() -> None:
            sys.exit("\nTerminated!\n")

        for sig in STOP_SIGNALS:
            loop.remove_signal_handler(sig)
            loop.add_signal_handler(sig, terminate)

    for sig in STOP_SIGNALS:
        loop.add_signal_handler(sig, stop_all)

    loop.run_until_complete(_main(stop_event))
