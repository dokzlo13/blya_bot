from __future__ import annotations

import tempfile
from datetime import datetime
from time import time

import structlog
from aiogram import types

from blya_bot.models import TextSummary, TranscriptionData
from blya_bot.recognition import BaseSpeechRecognizer, MediaType
from blya_bot.transcription_cache import BaseTranscriptionCache
from blya_bot.word_count import BaseWordCounter

logger = structlog.getLogger(__name__)


class BotCore:
    def __init__(
        self,
        recognizer: BaseSpeechRecognizer,
        word_counter: BaseWordCounter,
        cache: BaseTranscriptionCache | None = None,
    ) -> None:
        self.recognizer = recognizer
        self.word_counter = word_counter
        self.cache = cache

    async def transcribe_text(self, file_obj: types.Voice | types.VideoNote, media_type: MediaType) -> str:
        with tempfile.NamedTemporaryFile() as temp_audio_file:
            await file_obj.download(destination_file=temp_audio_file.file)
            temp_audio_file.seek(0)
            logger.debug("Voice file stored to temp", file=repr(temp_audio_file.name))
            logger.debug("Started transcribing voice")
            start_time = time()
            transcribed_text = await self.recognizer.recognize(temp_audio_file, media_type)
            logger.debug("Message transcribed", elapsed_time=f"{time()-start_time:.4f}sec.")
        return transcribed_text

    def calculate_summary(self, text: str) -> TextSummary:
        logger.debug("Counting words")
        start_time = time()
        summary = self.word_counter.calculate_summary(text)
        logger.debug("Words counted", elapsed_time=f"{time()-start_time:.4f}sec.")
        return summary

    async def transcribe_and_summarize(
        self, file_obj: types.Voice | types.VideoNote, media_type: MediaType
    ) -> TranscriptionData:
        if self.cache:
            cached = await self.cache.get(file_obj.file_unique_id)
            if cached:
                logger.debug("Transcription obtained from cache")
                return cached
        transcribed_text = await self.transcribe_text(file_obj, media_type)
        summary = self.calculate_summary(transcribed_text)
        data = TranscriptionData(
            transcription=transcribed_text,
            summary=summary,
            file_unique_id=file_obj.file_unique_id,
            date_processed=datetime.utcnow(),
        )
        if self.cache:
            await self.cache.store(file_obj.file_unique_id, data)
        return data

    @staticmethod
    def get_media(
        message: types.Message,
    ) -> tuple[types.Voice | types.VideoNote, MediaType]:
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
