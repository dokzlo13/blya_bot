import emoji  # type: ignore
import structlog
from aiogram import Bot, Dispatcher, types

from . import settings
from .core import BotCore
from .dictionary import count_words_total
from .recognition import MediaType
from .utils import highlight_text, split_in_chunks

logger = structlog.getLogger(__name__)


class TelegramViews:
    def __init__(self, core: BotCore) -> None:
        self.core = core

    async def handle_reply(self, message: types.Message):
        if message.reply_to_message.voice is None and message.reply_to_message.video_note is None:
            return
        if "расшифруй" not in message.text.lower():
            logger.debug("No magic words in message, skipping transcription")
            return

        file_obj, media_type = self.core.get_media(message.reply_to_message)
        if media_type == MediaType.VOICE and file_obj.duration > settings.SERVICE_MY_NERVES_LIMIT:
            return await message.reply(settings.SERVICE_MY_NERVES_LIMIT)

        with structlog.contextvars.bound_contextvars(
            # chat=repr(message.chat.full_name),
            message_id=message.message_id,
            chat_id=message.chat.id,
            file_unique_id=file_obj.file_unique_id,
            media_type=repr(media_type.name),
        ):
            transcribed_text = await self.core.transcribe_text(file_obj, media_type)
            summary = self.core.calculate_summary(transcribed_text)

            if len(summary.markup):
                highlighted = emoji.emojize(highlight_text(transcribed_text, summary.markup))
            else:
                highlighted = transcribed_text
            for msg_part in split_in_chunks(highlighted, 4096, ["\n\n", "\n", " "]):
                await message.reply_to_message.reply(msg_part, parse_mode=types.ParseMode.HTML)

    async def handle_media(self, message: types.Message):
        if message.forward_from is not None and settings.SERVICE_IGNORE_FORWARDED:
            logger.info("Forwarded audio skipped", message_id=message.message_id, chat_id=message.chat.id)
            return

        file_obj, media_type = self.core.get_media(message)
        if media_type == MediaType.VOICE and file_obj.duration > settings.SERVICE_MY_NERVES_LIMIT:
            return await message.reply(settings.SERVICE_MY_NERVES_LIMIT)

        with structlog.contextvars.bound_contextvars(
            # chat=repr(message.chat.full_name),
            message_id=message.message_id,
            chat_id=message.chat.id,
            file_unique_id=file_obj.file_unique_id,
            media_type=repr(media_type.name),
        ):
            transcribed_text = await self.core.transcribe_text(file_obj, media_type)
            summary = self.core.calculate_summary(transcribed_text)

            # highlighted = emoji.emojize(highlight_text(transcribed_text, summary.markup))
            # for msg_part in split_in_chunks(highlighted, 4096, ["\n\n", "\n", " "]):
            #     await message.reply(msg_part, parse_mode=types.ParseMode.HTML)

            # Overall stats
            bad_words_total = sum(summary.counter.values())
            if bad_words_total == 0:
                return

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


def build_bot(bot_token, bot_core: BotCore) -> Dispatcher:
    bot = Bot(token=bot_token)
    dp = Dispatcher(bot)
    views = TelegramViews(bot_core)

    dp.message_handler(is_reply=True)(views.handle_reply)
    dp.message_handler(content_types=[types.ContentType.VOICE, types.ContentType.VIDEO_NOTE])(views.handle_media)

    return dp
