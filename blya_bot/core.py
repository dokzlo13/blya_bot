import tempfile
from time import time

import emoji  # type: ignore
import structlog
from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_polling

from . import settings
from .dictionary import count_words_total
from .health import health_check_server
from .logging_conf import configure_logging
from .recognition import MediaType, SpeechRecognizer, get_recognizer_by_name
from .utils import highlight_text, split_in_chunks
from .word_count import TextSummary, WordCounter, keyword_tree_from_file

configure_logging(settings.SERVICE_LOG_LEVEL)

logger = structlog.getLogger(__name__)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Global state
# TODO: better global state management


bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher(bot)

logger.info("Loading bad words file", path=settings.SERVICE_BAD_WORDS_FILE)
logger.info("Creating bad words tree..")
kwtree = keyword_tree_from_file(settings.SERVICE_BAD_WORDS_FILE)
logger.info("Bad words tree created")

recognizer_cls = get_recognizer_by_name(settings.RECOGNITION_ENGINE)
logger.info("Loading speech recognition engine...", engine=settings.RECOGNITION_ENGINE)
recognizer: SpeechRecognizer = recognizer_cls.from_options(**settings.RECOGNITION_ENGINE_OPTIONS)
logger.info("Speech recognition engine loaded")

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


async def transcribe_text(file_obj: types.Voice | types.VideoNote, media_type: MediaType) -> str:
    with tempfile.NamedTemporaryFile() as temp_audio_file:
        await file_obj.download(destination_file=temp_audio_file.file)
        temp_audio_file.seek(0)
        logger.debug("Voice file stored to temp", file=repr(temp_audio_file.name))
        logger.debug("Started transcribing voice")
        start_time = time()
        transcribed_text = await recognizer.recognize(temp_audio_file, media_type)
        logger.debug("Message transcribed", elapsed_time=f"{time()-start_time:.4f}sec.")
    return transcribed_text


def calculate_summary(text: str) -> TextSummary:
    logger.debug("Counting words")
    start_time = time()
    word_counter = WordCounter(kwtree)
    word_counter.feed(text)
    summary = word_counter.summary()
    logger.debug("Words counted", elapsed_time=f"{time()-start_time:.4f}sec.")
    return summary


def get_media(message: types.Message) -> tuple[types.Voice | types.VideoNote, MediaType]:
    if message.video_note:
        file_obj = message.video_note
        media_type = MediaType.VIDEO_NOTE
    elif message.voice:
        file_obj = message.voice
        media_type = MediaType.VOICE
    else:
        # Unreachable
        raise Exception("Can't extract media")
    return file_obj, media_type


@dp.message_handler(is_reply=True)
async def handle_reply(message: types.Message):
    if message.reply_to_message.voice is None and message.reply_to_message.video_note is None:
        return
    file_obj, media_type = get_media(message.reply_to_message)
    if media_type == MediaType.VOICE and file_obj.duration > settings.SERVICE_MY_NERVES_LIMIT:
        return await message.reply(settings.SERVICE_MY_NERVES_LIMIT)

    with structlog.contextvars.bound_contextvars(
        # chat=repr(message.chat.full_name),
        message_id=message.message_id,
        chat_id=message.chat.id,
        file_unique_id=file_obj.file_unique_id,
        media_type=repr(media_type.name),
    ):
        transcribed_text = await transcribe_text(file_obj, media_type)
        summary = calculate_summary(transcribed_text)

        highlighted = emoji.emojize(highlight_text(transcribed_text, summary.markup))
        for msg_part in split_in_chunks(highlighted, 4096, ["\n\n", "\n", " "]):
            await message.reply_to_message.reply(msg_part, parse_mode=types.ParseMode.HTML)


@dp.message_handler(content_types=[types.ContentType.VOICE, types.ContentType.VIDEO_NOTE])
async def handle_voice(message: types.Message):
    if message.forward_from is not None and settings.SERVICE_IGNORE_FORWARDED:
        logger.info("Forwarded audio skipped", message_id=message.message_id, chat_id=message.chat.id)
        return

    file_obj, media_type = get_media(message)
    if media_type == MediaType.VOICE and file_obj.duration > settings.SERVICE_MY_NERVES_LIMIT:
        return await message.reply(settings.SERVICE_MY_NERVES_LIMIT)

    with structlog.contextvars.bound_contextvars(
        # chat=repr(message.chat.full_name),
        message_id=message.message_id,
        chat_id=message.chat.id,
        file_unique_id=file_obj.file_unique_id,
        media_type=repr(media_type.name),
    ):
        transcribed_text = await transcribe_text(file_obj, media_type)
        summary = calculate_summary(transcribed_text)

        # Overall stats
        bad_words_total = sum(summary.counter.values())
        words_total = count_words_total(transcribed_text)
        bad_words_percentage = (bad_words_total / words_total) * 100

        # Assembling answer
        response_text = "<b><i>Cтатистика:</i></b>\n"
        for word, cnt in summary.counter.items():
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

    logger.info("Skipping updates...")
    await dp.reset_webhook(True)
    await dp.skip_updates()

    logger.info(f"Configuring webhook: {webhook_url!r}")
    is_wh_set = await bot.set_webhook(webhook_url)
    if is_wh_set:
        logger.info("Webhook set")
    else:
        logger.error("Webhook not set!")
        raise SystemExit()


async def on_shutdown(app):
    logger.info("Deleting webhook")
    is_wh_del = await bot.delete_webhook()
    if is_wh_del:
        logger.info("Webhook deleted")
    else:
        logger.error("Webhook not deleted!")


def main():
    with health_check_server(
        lambda: True, settings.HEALTH_CHECK_HOST, settings.HEALTH_CHECK_PORT, settings.HEALTH_CHECK_PATH
    ):
        if settings.TELEGRAM_USE_WEBHOOK:
            # TODO: implement webhook
            pass
            # logger.info("Starting in webhook mode")
            # from aiogram.dispatcher.webhook import configure_app

            # app.on_startup.append(on_startup)
            # app.on_shutdown.append(on_shutdown)
            # configure_app(dp, app, path=settings.WEBHOOK_PATH)
            # try:
            #     web.run_app(app, host=settings.HTTP_HOST, port=settings.HTTP_PORT)
            # except SystemExit:
            #     logger.info("Server exitted")

        else:
            logger.info("Starting in polling mode")
            start_polling(dp, skip_updates=True)
    logger.info("Bye!")
