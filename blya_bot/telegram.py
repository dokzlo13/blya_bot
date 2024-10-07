import tempfile
from typing import Awaitable, Callable

import emoji  # type: ignore
import structlog
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode

from blya_bot.models.models import TranscriptionData

from . import settings
from .core import BotCore
from .utils import highlight_text, split_in_chunks
from .word_count.utils import count_words_total

logger = structlog.getLogger(__name__)


class TelegramViews:
    def __init__(self, core: BotCore, bot: Bot) -> None:
        self.core = core
        self.bot = bot

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    async def handle_voice_reply(self, message: types.Message):
        if message.reply_to_message is None:
            return

        # if message.forward_from is not None and settings.SERVICE_IGNORE_FORWARDED:
        #     logger.info("Forwarded audio skipped", message_id=message.message_id, chat_id=message.chat.id)
        #     return

        message = message.reply_to_message
        if message.voice is None:
            return

        if message.forward_from is not None and settings.SERVICE_IGNORE_FORWARDED:
            logger.info("Forwarded audio skipped", message_id=message.message_id, chat_id=message.chat.id)
            return

        if message.voice.duration > settings.SERVICE_MY_NERVES_LIMIT:
            return await message.reply(settings.SERVICE_MY_NERVES_LIMIT)

        with structlog.contextvars.bound_contextvars(message_id=message.message_id, chat_id=message.chat.id):
            data = await self.transcribe_media(message.voice.file_id, message.voice.file_unique_id)
            return await self.answer_transcription(message, data)

    async def handle_video_note_reply(self, message: types.Message):
        if message.reply_to_message is None:
            return

        # if message.forward_from is not None and settings.SERVICE_IGNORE_FORWARDED:
        #     logger.info("Forwarded audio skipped", message_id=message.message_id, chat_id=message.chat.id)
        #     return

        message = message.reply_to_message
        if message.video_note is None:
            return

        with structlog.contextvars.bound_contextvars(message_id=message.message_id, chat_id=message.chat.id):
            data = await self.transcribe_media(message.video_note.file_id, message.video_note.file_unique_id)
            return await self.answer_transcription(message, data)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    async def handle_voice(self, message: types.Message):
        if message.voice is None:
            return

        if message.forward_from is not None and settings.SERVICE_IGNORE_FORWARDED:
            logger.info("Forwarded audio skipped", message_id=message.message_id, chat_id=message.chat.id)
            return

        if message.voice.duration > settings.SERVICE_MY_NERVES_LIMIT:
            return await message.reply(settings.SERVICE_MY_NERVES_LIMIT)

        with structlog.contextvars.bound_contextvars(message_id=message.message_id, chat_id=message.chat.id):
            data = await self.transcribe_media(message.voice.file_id, message.voice.file_unique_id)
            return await self.answer_summary(message, data)

    async def handle_video_note(self, message: types.Message):
        if message.video_note is None:
            return

        with structlog.contextvars.bound_contextvars(message_id=message.message_id, chat_id=message.chat.id):
            data = await self.transcribe_media(message.video_note.file_id, message.video_note.file_unique_id)
            return await self.answer_summary(message, data)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    async def transcribe_media(self, file_id: str, file_unique_id: str) -> TranscriptionData:
        with (
            structlog.contextvars.bound_contextvars(file_unique_id=file_unique_id),
            tempfile.NamedTemporaryFile() as temp_audio_file,
        ):
            await self.bot.download(file_id, destination=temp_audio_file)  # type: ignore
            temp_audio_file.seek(0)
            logger.debug("Voice file stored to temp", file=repr(temp_audio_file.name), file_id=file_id)
            return await self.core.transcribe_and_summarize(file_unique_id, temp_audio_file)

    async def answer_summary(self, message: types.Message, data: TranscriptionData):
        # Overall stats
        bad_words_total = sum(data.summary.counter.values())
        if bad_words_total == 0:
            # TODO: template response messages
            response_text = "Я не обнаружил ругательств, :red_heart: <b>вы восхитительны</b> :red_heart:"
            return await message.reply(emoji.emojize(response_text), parse_mode=ParseMode.HTML)

        words_total = count_words_total(data.transcription)
        bad_words_percentage = (bad_words_total / words_total) * 100

        # Assembling answer
        # TODO: template response messages
        response_text = "<b><i>Cтатистика:</i></b>\n"
        for word, cnt in data.summary.counter.most_common():  # Sorted by count from high to low
            response_text += f":sparkles: <b>{word}</b> - {cnt}\n"
        response_text += (
            f"\nВсего около <b>{bad_words_total}</b> матерных слов из <b>{words_total}</b> "
            f"или <b>{bad_words_percentage:.2f}%</b> :new_moon_face:"
        )

        return await message.reply(emoji.emojize(response_text), parse_mode=ParseMode.HTML)

    async def answer_transcription(self, message: types.Message, data: TranscriptionData):
        if len(data.summary.markup):
            highlighted = emoji.emojize(highlight_text(data.transcription, data.summary.markup))
        else:
            highlighted = data.transcription
        for msg_part in split_in_chunks(highlighted, 4096, ["\n\n", "\n", " "]):
            await message.reply(msg_part, parse_mode=ParseMode.HTML)


def build_bot(bot_token, bot_core: BotCore, transcribe_command: str = "/transcribe") -> tuple[Bot, Dispatcher]:
    bot = Bot(token=bot_token)
    dp = Dispatcher()
    views = TelegramViews(bot_core, bot)

    dp.message(F.voice.is_not(None))(views.handle_voice)
    dp.message(F.video_note.is_not(None))(views.handle_video_note)

    dp.message(
        F.reply_to_message.is_not(None) & F.reply_to_message.voice.is_not(None) & F.text.contains(transcribe_command)
    )(views.handle_voice_reply)
    dp.message(
        F.reply_to_message.is_not(None)
        & F.reply_to_message.video_note.is_not(None)
        & F.text.contains(transcribe_command)
    )(
        views.handle_video_note_reply,
    )

    return bot, dp
