import io
import json
import wave
from collections import Counter
from typing import Generator

import emoji
import pydub
import vosk
from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_polling

from . import settings
from .tools import async_wrap_iter
from .health import HealthCheckApp

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher(bot)

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


def recognize(wav_buf: io.IOBase) -> Generator[None, str, None]:
    # Loading as wave to obtain framerate for recognizer
    wf = wave.open(wav_buf, "rb")  # type: ignore

    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
        print("Audio file must be WAV format mono PCM.")

    rec = vosk.KaldiRecognizer(speech_model, wf.getframerate())
    # rec.SetWords(True)
    # rec.SetPartialWords(True)
    rec.SetNLSML(True)

    while True:
        data = wav_buf.read(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            yield json.loads(rec.Result())["text"]

    yield json.loads(rec.FinalResult())["text"]


def count_words(text, words) -> Counter:
    counts = Counter({w: 0 for w in words})
    for word in words:
        counts[word] += text.count(word)
    return counts


def count_words_total(text) -> int:
    return len(text.split())


@dp.message_handler(content_types=types.ContentType.VOICE)
async def handle_voice(message: types.Message):
    if message.voice.duration > settings.MY_NERVES_LIMIT:
        return await message.reply(settings.POLITE_RESPONSE)

    # Downloading file. Yes, right in memory
    ogg_buf = io.BytesIO()
    await message.voice.download(destination_file=ogg_buf)
    ogg_buf.seek(0)

    # Converting audio file from "ogg" to "wav"
    audio: pydub.AudioSegment = pydub.AudioSegment.from_ogg(ogg_buf)
    audio = audio.set_channels(1)
    audio = audio.set_sample_width(2)

    wav_buf = io.BytesIO()
    audio.export(format="wav", out_f=wav_buf)
    wav_buf.seek(0)

    # Counting words
    counts: Counter = Counter()
    full_text = ""
    async for text in async_wrap_iter(recognize(wav_buf)):
        full_text += text
        counts += count_words(text, settings.COUNT_WORDS)

    counts = Counter({w: c for w, c in dict(counts).items() if c > 0})  # type: ignore
    if not len(counts):
        return

    # Assembling answer
    bad_words_total = sum(counts.values())
    words_total = count_words_total(full_text)
    response_text = "<b><i>Cтатистика:</i></b>\n"
    for word, cnt in counts.items():
        response_text += f":sparkles: <b>{word}</b> - {cnt}\n"
    response_text += (
        f"\nВсего около <b>{bad_words_total}</b> матерных слов из <b>{words_total}</b> "
        f"или <b>{(bad_words_total / words_total) * 100:.2f}%</b> :new_moon_face:"
    )

    await message.reply(emoji.emojize(response_text), parse_mode=types.ParseMode.HTML)


def main():
    start_polling(dp, skip_updates=True, on_startup=start_health_check, on_shutdown=stop_health_check)
