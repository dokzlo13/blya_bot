from os import getenv

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = getenv("BOT_TOKEN")
VOSK_MODEL_PATH = getenv("VOSK_MODEL_PATH", "./models/vosk-model-ru-0.22")
COUNT_WORDS = ["бля", "пидор", "ебать", "хуй", "сука"]
MY_NERVES_LIMIT = 5 * 60
POLITE_RESPONSE = "Бот сломан, больше пяти минут войса ему не переварить"
