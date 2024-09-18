import asyncio
import signal
import sys
from pathlib import Path

import aiosqlite
import structlog

# from aiogram.utils import executor
from . import settings
from .core import BotCore
from .dictionary import DslFileDict, IDictionaryLoader, PyMorphyRuDictModifier
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
from .word_count import AhoCorasickWordCounter, BaseWordCounter

logger = structlog.getLogger(__name__)
STOP_SIGNALS = (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)


def load_recognition_core() -> BaseSpeechRecognizer:
    recognizer_cls = get_recognizer_by_name(settings.RECOGNITION_ENGINE)
    logger.info("Loading speech recognition engine...", engine=recognizer_cls.__name__)
    recognizer: BaseSpeechRecognizer = recognizer_cls.from_options(**settings.RECOGNITION_ENGINE_OPTIONS)
    logger.info("Speech recognition engine loaded")
    return recognizer


def load_word_counter() -> BaseWordCounter:
    loader = DslFileDict(equal_chars=[("е", "ё"), ("и", "й")])
    logger.info("Dict loader created", engine="DslFileDict")

    logger.info("Loading dictionary file...", path=settings.SERVICE_BAD_WORDS_FILE)
    dictionary = loader.load(settings.SERVICE_BAD_WORDS_FILE)
    logger.info("Dict loaded", total_loaded=len(dictionary))

    logger.info("Morphing word forms...")
    dictionary = PyMorphyRuDictModifier().modify_dict(dictionary)
    logger.info("Dict morphed", total_morphed=len(dictionary))

    logger.info("Assembling automata...")
    return AhoCorasickWordCounter.from_dictionary(dictionary)


async def make_cache() -> BaseTranscriptionCache:
    cache: BaseTranscriptionCache
    if settings.CACHE_ENGINE == "memory":
        ttl = settings.CACHE_PARAMS["ttl"]
        cache = InMemoryTranscriptionCache(ttl)
        logger.info("Cache engine loaded", ttl=ttl, engine="InMemoryTranscriptionCache")
    elif settings.CACHE_ENGINE == "sqlite":
        db_path = settings.CACHE_PARAMS["db_path"]
        ttl = settings.CACHE_PARAMS.get("ttl", None)
        conn = await aiosqlite.connect(db_path)
        cache = SqliteTranscriptionCache(conn, ttl)
        logger.info("Cache engine loaded", db_path=db_path, ttl=ttl, engine="SqliteTranscriptionCache")
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
        bot, dispatcher = build_bot(settings.TELEGRAM_BOT_TOKEN, bot_core)

        # Hacking executor, to work inside current running loop
        # ex = executor.Executor(dispatcher=dispatcher, skip_updates=True, loop=loop)

        # async def master_task():
        #     ex._prepare_polling()
        #     await ex._startup_polling()
        #     try:
        #         await ex.dispatcher.start_polling(
        #             reset_webhook=None, timeout=20, relax=0.1, fast=True, allowed_updates=None
        #         )
        #     finally:
        #         await ex._shutdown_polling()

        await dispatcher.start_polling(bot)

        # task = asyncio.create_task()
        # await stop_event.wait()
        await cache.teardown()

        # if not task.done():
        #     task.cancel()

        # try:
        #     await task
        # except asyncio.CancelledError:
        #     logger.warning(f"Task {task.get_name()!r} terminated")


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
