import asyncio
import signal
import sys

import aiosqlite
import structlog
from aiogram.utils import executor

from . import settings
from .core import BotCore
from .dictionary import BaseDictionaryLoader, DslDictLoader, PyMorphyRuDslDictLoader
from .health import async_health_check_server
from .logging_conf import configure_logging
from .recognition import BaseSpeechRecognizer, get_recognizer_by_name
from .telegram import build_bot
from .transcription_cache import (
    BaseTranscriptionCache,
    InMemoryTranscriptionCache,
    NullTranscriptionCache,
    SqliteTranscriptionCache,
)
from .word_count import BaseWordCounter, KWTreeWordCounter

logger = structlog.getLogger(__name__)
STOP_SIGNALS = (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)


def load_recognition_core() -> BaseSpeechRecognizer:
    recognizer_cls = get_recognizer_by_name(settings.RECOGNITION_ENGINE)
    logger.info("Loading speech recognition engine...", engine=recognizer_cls.__name__)
    recognizer: BaseSpeechRecognizer = recognizer_cls.from_options(**settings.RECOGNITION_ENGINE_OPTIONS)
    logger.info("Speech recognition engine loaded")
    return recognizer


def load_word_counter() -> BaseWordCounter:
    loader: BaseDictionaryLoader
    try:
        loader = PyMorphyRuDslDictLoader()
        logger.info("Dict loader created", engine="PyMorphyRuDslDictLoader")
    except ImportError:
        logger.warning("Morphological extension dependencies not installed, falling back to DslDictLoader")
        loader = DslDictLoader()
        logger.info("Dict loader created", engine="DslDictLoader")

    logger.info("Loading dictionary file", path=settings.SERVICE_BAD_WORDS_FILE)
    dictionary = loader.load_dictionary(settings.SERVICE_BAD_WORDS_FILE)
    kwtree = KWTreeWordCounter.from_dictionary(dictionary)
    return kwtree


async def make_cache() -> BaseTranscriptionCache:
    cache: BaseTranscriptionCache
    if settings.CACHE_ENGINE == "memory":
        ttl = settings.CACHE_PARAMS["ttl"]
        cache = InMemoryTranscriptionCache(ttl)
        logger.info("Cache engine loaded", ttl=ttl, engine="InMemoryTranscriptionCache")
    elif settings.CACHE_ENGINE == "sqlite":
        db_path = settings.CACHE_PARAMS["db_path"]
        conn = await aiosqlite.connect(db_path)
        cache = SqliteTranscriptionCache(conn)
        logger.info("Cache engine loaded", db_path=db_path, engine="SqliteTranscriptionCache")
    else:
        cache = NullTranscriptionCache()
        logger.warning("Cache settings not defined, cache disabled")
    return cache


async def _main(stop_event: asyncio.Event, loop):
    configure_logging(settings.SERVICE_LOG_LEVEL)

    logger.info("Creating bot core...")

    cache = await make_cache()
    await cache.setup()
    bot_core = BotCore(load_recognition_core(), load_word_counter(), cache=cache)
    logger.info("Bot core assembled")

    logger.info("Starting bot...")
    async with async_health_check_server(
        lambda: True, settings.HEALTH_CHECK_HOST, settings.HEALTH_CHECK_PORT, settings.HEALTH_CHECK_PATH, loop=loop
    ):
        dispatcher = build_bot(settings.TELEGRAM_BOT_TOKEN, bot_core)

        # Hacking executor, to work inside current running loop
        ex = executor.Executor(dispatcher=dispatcher, skip_updates=True, loop=loop)

        async def master_task():
            ex._prepare_polling()
            await ex._startup_polling()
            try:
                await ex.dispatcher.start_polling(
                    reset_webhook=None, timeout=20, relax=0.1, fast=True, allowed_updates=None
                )
            finally:
                await ex._shutdown_polling()

        task = asyncio.create_task(master_task())
        await stop_event.wait()
        await cache.teardown()

        if not task.done():
            task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            logger.warning(f"Task {task.get_name()!r} terminated")


# def _main():
#     configure_logging(settings.SERVICE_LOG_LEVEL)

#     logger.info("Creating bot core...")
#     bot_core = BotCore(load_recognition_core(), load_word_counter(), cache=InMemoryTranscriptionCache())
#     logger.info("Bot core assembled")

#     logger.info("Starting bot...")
#     with health_check_server(
#         lambda: True, settings.HEALTH_CHECK_HOST, settings.HEALTH_CHECK_PORT, settings.HEALTH_CHECK_PATH
#     ):
#         dispatcher = build_bot(settings.TELEGRAM_BOT_TOKEN, bot_core)
#         executor.start_polling(dispatcher, skip_updates=True)


def main():

    loop = asyncio.new_event_loop()

    stop_event = asyncio.Event()

    def stop_all() -> None:
        stop_event.set()
        logger.warning("Shutting down service! Press ^C again to terminate")

        def terminate():
            sys.exit("\nTerminated!\n")

        for sig in STOP_SIGNALS:
            loop.remove_signal_handler(sig)
            loop.add_signal_handler(sig, terminate)

    for sig in STOP_SIGNALS:
        loop.add_signal_handler(sig, stop_all)

    loop.run_until_complete(_main(stop_event, loop))
