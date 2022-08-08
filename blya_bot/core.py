import io
import logging
from time import time

import emoji  # type: ignore
import vosk
from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_polling

from . import settings
from .audio import convert_ogg_to_wav
from .recognition import SpeechRecognizer
from .word_count import WordCounter, count_words_total, keyword_tree_from_file

# TODO: better logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Global state
# TODO: better global state management


bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher(bot)

logging.info("Creating bad words tree..")
kwtree = keyword_tree_from_file(settings.BAD_WORDS_FILE)
logging.info("Bad words tree created")

logging.info("Loading model...")
speech_model = vosk.Model(model_path=settings.VOSK_MODEL_PATH)
logging.info("Model loaded")

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


@dp.message_handler(content_types=types.ContentType.VOICE)
async def handle_voice(message: types.Message):
    if message.forward_from is not None:
        logging.info("Repost audio skipped")
        return

    if message.voice.duration > settings.MY_NERVES_LIMIT:
        return await message.reply(settings.POLITE_RESPONSE)

    start_time = time()
    # Downloading file. Yes, right in memory
    ogg_buf = io.BytesIO()
    await message.voice.download(destination_file=ogg_buf)
    ogg_buf.seek(0)

    wav_buf = convert_ogg_to_wav(ogg_buf)
    del ogg_buf
    recognizer = SpeechRecognizer(speech_model)

    # Counting words
    word_counter = WordCounter(kwtree)
    full_text = ""
    async for text in recognizer.recognize(wav_buf):
        full_text += text
        word_counter.feed(text)
    del wav_buf

    counts = word_counter.summary()
    logging.info(f"Message transcripted, elapsed time: {time()-start_time:.4f}sec.")
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

    return await message.reply(emoji.emojize(response_text), parse_mode=types.ParseMode.HTML)


async def on_startup(app):
    if settings.WEBHOOK_URL:
        webhook_url = settings.WEBHOOK_URL
    else:
        webhook_url = f"https://{settings.HTTP_HOST}:{settings.HTTP_PORT}{settings.WEBHOOK_PATH}"

    logging.info(f"Configuring webhook: {webhook_url!r}")
    await bot.set_webhook(webhook_url)
    logging.info("Webhook set")


async def on_shutdown(app):
    logging.info("Deleting webhook")
    await bot.delete_webhook()
    logging.info("Webhook deleted")


def main():
    from aiohttp import web

    from .health import add_health_check_probe

    app = web.Application()
    add_health_check_probe(app, lambda: True)

    if settings.WEBHOOK_PATH:
        logging.info("Starting in webhook mode")
        from aiogram.dispatcher.webhook import configure_app

        app.on_startup.append(on_startup)
        app.on_shutdown.append(on_shutdown)
        configure_app(dp, app, path=settings.WEBHOOK_PATH)
        try:
            return web.run_app(app, host=settings.HTTP_HOST, port=settings.HTTP_PORT)
        except SystemExit:
            logging.info("Server exitted")

    else:
        logging.info("Starting in polling mode")
        from .web_utils import BackgroundAppRunner

        runner = BackgroundAppRunner(app)
        runner.start_http_server(host=settings.HTTP_HOST, port=settings.HTTP_PORT)
        start_polling(dp, skip_updates=True)
        runner.stop_http_server()
