import structlog
from aiogram.utils import executor

from . import settings
from .core import BotCore
from .health import health_check_server
from .logging_conf import configure_logging
from .recognition import SpeechRecognizer, get_recognizer_by_name
from .telegram import build_bot
from .word_count import WordCounterEngine

logger = structlog.getLogger(__name__)


def load_recognition_core() -> SpeechRecognizer:
    recognizer_cls = get_recognizer_by_name(settings.RECOGNITION_ENGINE)
    logger.info("Loading speech recognition engine...", engine=settings.RECOGNITION_ENGINE)
    recognizer: SpeechRecognizer = recognizer_cls.from_options(**settings.RECOGNITION_ENGINE_OPTIONS)
    logger.info("Speech recognition engine loaded")
    return recognizer


def load_word_counter() -> WordCounterEngine:
    logger.info("Loading bad words file", path=settings.SERVICE_BAD_WORDS_FILE)
    logger.info("Creating bad words tree..")
    kwtree = WordCounterEngine.from_file(settings.SERVICE_BAD_WORDS_FILE)
    logger.info("Bad words tree created")
    return kwtree


def main():
    configure_logging(settings.SERVICE_LOG_LEVEL)

    bot_core = BotCore(load_recognition_core(), load_word_counter())

    with health_check_server(
        lambda: True, settings.HEALTH_CHECK_HOST, settings.HEALTH_CHECK_PORT, settings.HEALTH_CHECK_PATH
    ):
        dispatcher = build_bot(settings.TELEGRAM_BOT_TOKEN, bot_core)
        executor.start_polling(dispatcher, skip_updates=True)
