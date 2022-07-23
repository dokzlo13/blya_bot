import io

import emoji  # types: ignore
import vosk
from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_polling

from . import settings
from .audio import convert_ogg_to_wav
from .health import HealthCheckApp
from .recognition import SpeechRecognizer
from .word_count import WordCounter, count_words_total, keyword_tree_from_file

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Global state
# TODO: better global state management

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher(bot)

print("Creating bad words tree..")
kwtree = keyword_tree_from_file(settings.BAD_WORDS_FILE)
print("Bad words tree created")

print("Loading model...")
speech_model = vosk.Model(model_path=settings.VOSK_MODEL_PATH)
print("Model loaded")

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Health check app

health_check_app = HealthCheckApp(lambda: True, port=settings.HEALTH_CHECK_PORT)


async def start_health_check(*args):
    await health_check_app.start_http_server()


async def stop_health_check(*args):
    await health_check_app.stop_http_server()


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


@dp.message_handler(content_types=types.ContentType.VOICE)
async def handle_voice(message: types.Message):
    if message.voice.duration > settings.MY_NERVES_LIMIT:
        return await message.reply(settings.POLITE_RESPONSE)

    # Downloading file. Yes, right in memory
    ogg_buf = io.BytesIO()
    await message.voice.download(destination_file=ogg_buf)
    ogg_buf.seek(0)

    wav_buf = await convert_ogg_to_wav(ogg_buf)
    recognizer = SpeechRecognizer(speech_model)

    # Counting words
    word_counter = WordCounter(kwtree)
    full_text = ""
    async for text in recognizer.recognize(wav_buf):
        full_text += text
        word_counter.feed(text)

    counts = word_counter.summary()
    if not len(counts):
        return

    # Overall stats
    bad_words_total = sum(counts.values())
    words_total = count_words_total(full_text)
    bad_words_percentage = (bad_words_total / words_total) * 100

    # Assembling answer
    response_text = "<b><i>Cтатистика:</i></b>\n"
    for word, cnt in counts.items():
        response_text += f":sparkles: <b>{word}</b> - {cnt}\n"
    response_text += (
        f"\nВсего около <b>{bad_words_total}</b> матерных слов из <b>{words_total}</b> "
        f"или <b>{bad_words_percentage:.2f}%</b> :new_moon_face:"
    )

    await message.reply(emoji.emojize(response_text), parse_mode=types.ParseMode.HTML)


def main():
    start_polling(dp, skip_updates=True, on_startup=start_health_check, on_shutdown=stop_health_check)
