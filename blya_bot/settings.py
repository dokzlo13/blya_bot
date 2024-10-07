import structlog
from environs import Env

logger = structlog.getLogger(__name__)

AVAILABLE_RECOGNITION_ENGINES = ("vosk", "pywhispercpp", "faster-whisper")

env = Env()
env.read_env()


TELEGRAM_BOT_TRANSCRIBE_COMMAND = env("TELEGRAM_BOT_TRANSCRIBE_COMMAND", "/t")
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
SERVICE_LOG_COLORS = env.bool("SERVICE_LOG_COLORS", False)
SERVICE_BAD_WORDS_FILE = env.path("SERVICE_BAD_WORDS_FILE", "./fixtures/bad_words.txt")

RECOGNITION_ENGINE = env("RECOGNITION_ENGINE").lower()
if RECOGNITION_ENGINE not in AVAILABLE_RECOGNITION_ENGINES:
    raise Exception(
        f"Please choose supported recognition engine: {', '.join(AVAILABLE_RECOGNITION_ENGINES)}, not {RECOGNITION_ENGINE!r}"
    )
RECOGNITION_ENGINE_OPTIONS = env.json("RECOGNITION_ENGINE_OPTIONS", "{}")

if RECOGNITION_ENGINE == "vosk":
    if RECOGNITION_ENGINE_OPTIONS.get("model_path") is None:
        raise Exception("Please provide 'model_path' option in 'RECOGNITION_ENGINE_OPTIONS' config")

elif RECOGNITION_ENGINE in ("pywhispercpp", "faster-whisper") and RECOGNITION_ENGINE_OPTIONS.get("model") is None:
    raise Exception("Please provide 'model' option in 'RECOGNITION_ENGINE_OPTIONS' config")

HEALTH_CHECK_HOST = env("HEALTH_CHECK_HOST", "0.0.0.0")  # noqa: S104
HEALTH_CHECK_PORT = env.int("HEALTH_CHECK_PORT", 8080)
HEALTH_CHECK_PATH = env("HEALTH_CHECK_PATH", "/health/live")

CACHE_ENGINE = env("CACHE_ENGINE", None)
CACHE_PARAMS = env.json("CACHE_PARAMS", "{}")
if CACHE_ENGINE == "sqlite":
    if CACHE_PARAMS.get("db_path") is None:
        CACHE_PARAMS["db_path"] = "transcription_cache.db"
elif CACHE_ENGINE == "memory":
    if CACHE_PARAMS.get("ttl") is None:
        CACHE_PARAMS["ttl"] = 60 * 60
elif CACHE_ENGINE is None:
    pass
else:
    raise Exception("CACHE_ENGINE can be only 'sqlite' or 'memory'")
