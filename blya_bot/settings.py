from os import getenv

from dotenv import load_dotenv

load_dotenv()

# TODO: better settings

BOT_TOKEN = getenv("BOT_TOKEN")
VOSK_MODEL_PATH = getenv("VOSK_MODEL_PATH", "./models/vosk-model-ru-0.22")
BAD_WORDS_FILE = getenv("BAD_WORDS_FILE", "./fixtures/bad_words.txt")

WEBHOOK_PATH = getenv("WEBHOOK_PATH", None)  # "/webhook"
if WEBHOOK_PATH is not None and not WEBHOOK_PATH.startswith("/"):
    raise Exception("'WEBHOOK_PATH' must begin with '/'")

WEBHOOK_URL = getenv("WEBHOOK_URL", None)  # "https://my-server.com/webhook"
HTTP_PORT = getenv("WEBHOOK_PORT", 8080)
HTTP_HOST = getenv("WEBHOOK_HOST", "localhost")

MY_NERVES_LIMIT = 5 * 60
POLITE_RESPONSE = "Бот сломан, больше пяти минут войса ему не переварить"
