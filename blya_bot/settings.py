from os import getenv

from dotenv import load_dotenv

load_dotenv()

# TODO: better settings

BOT_TOKEN = getenv("BOT_TOKEN")
VOSK_MODEL_PATH = getenv("VOSK_MODEL_PATH", "./models/vosk-model-ru-0.22")
HEALTH_CHECK_PORT = int(getenv("HEALTH_CHECK_PORT", 8080))
BAD_WORDS_FILE = getenv("BAD_WORDS_FILE", "./fixtures/bad_words.txt")
MY_NERVES_LIMIT = 5 * 60
POLITE_RESPONSE = "Бот сломан, больше пяти минут войса ему не переварить"
