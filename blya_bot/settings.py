import os

import environs
import structlog

logger = structlog.getLogger(__name__)


class Env(environs.Env):
    @staticmethod
    def read_env(
        path: str | None = None,
        recurse: bool = True,
        verbose: bool = False,
        override: bool = False,
    ) -> None:
        env_files = ("settings.cfg", ".env")
        for env_file in env_files:
            if os.path.isfile(env_file):
                path = env_file
                logger.info(f"Loading settings file: {path}")
                return environs.Env.read_env(path, recurse, verbose, override)

        logger.warning("Settings file not found! Using the default values")
        return environs.Env.read_env(path, recurse, verbose, override)


AVAILABLE_RECOGNITION_ENGINES = ("whisper", "vosk")

env = Env()
env.read_env()

TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN")
TELEGRAM_USE_WEBHOOK = env.bool("TELEGRAM_USE_WEBHOOK", False)
if TELEGRAM_USE_WEBHOOK:
    TELEGRAM_WEBHOOK_URL = env("TELEGRAM_WEBHOOK_URL", None)  # "https://my-server.com/webhook"
    TELEGRAM_WEBHOOK_PATH = env("TELEGRAM_WEBHOOK_PATH", "/webhook")  # "/webhook"
    if not TELEGRAM_WEBHOOK_PATH.startswith("/"):
        raise Exception("'TELEGRAM_WEBHOOK_PATH' must begin with '/'")
else:
    TELEGRAM_WEBHOOK_URL = None
    TELEGRAM_WEBHOOK_PATH = None


SERVICE_MY_NERVES_LIMIT = env.int("SERVICE_POLITE_RESPONSE", 5 * 60)
SERVICE_POLITE_RESPONSE = env("SERVICE_POLITE_RESPONSE", "Бот сломан, больше пяти минут войса ему не переварить")
SERVICE_IGNORE_FORWARDED = env.bool("SERVICE_IGNORE_FORWARDED", True)
SERVICE_LOG_LEVEL = env("SERVICE_LOG_LEVEL", "info")
SERVICE_BAD_WORDS_FILE = env("SERVICE_BAD_WORDS_FILE", "./fixtures/bad_words.txt")

RECOGNITION_ENGINE = env("RECOGNITION_ENGINE", "whisper").lower()
if RECOGNITION_ENGINE not in AVAILABLE_RECOGNITION_ENGINES:
    raise Exception(f"Please choose supported recognition engine: {', '.join(AVAILABLE_RECOGNITION_ENGINES)}")
RECOGNITION_ENGINE_OPTIONS = env.json("RECOGNITION_ENGINE_OPTIONS", "{}")

if RECOGNITION_ENGINE == "vosk":
    if RECOGNITION_ENGINE_OPTIONS.get("model_path") is None:
        raise Exception("Please provide 'model_path' option in 'RECOGNITION_ENGINE_OPTIONS' env")
elif RECOGNITION_ENGINE == "whisper":
    if RECOGNITION_ENGINE_OPTIONS.get("model_name") is None:
        raise Exception("Please provide 'model_name' option in 'RECOGNITION_ENGINE_OPTIONS' env")

HEALTH_CHECK_HOST = env("HEALTH_CHECK_HOST", "0.0.0.0")
HEALTH_CHECK_PORT = env.int("HEALTH_CHECK_HOST", 8080)
HEALTH_CHECK_PATH = env("HEALTH_CHECK_PATH", "/health/live")
