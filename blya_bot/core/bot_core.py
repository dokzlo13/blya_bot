from __future__ import annotations

from datetime import datetime
from tempfile import _TemporaryFileWrapper as TempFile
from time import time

import structlog
from aiogram import types

from blya_bot.models import TextSummary, TranscriptionData
from blya_bot.recognition import BaseSpeechRecognizer
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

    async def transcribe_text(self, file: TempFile) -> str:
        logger.debug("Started transcribing voice")
        start_time = time()
        transcribed_text = await self.recognizer.recognize(file)
        logger.debug("Message transcribed", elapsed_time=f"{time()-start_time:.4f}sec.")
        return transcribed_text

    def calculate_summary(self, text: str) -> TextSummary:
        logger.debug("Counting words")
        start_time = time()
        summary = self.word_counter.calculate_summary(text.lower())  # TODO: Maybe better text preparation for counting
        logger.debug("Words counted", elapsed_time=f"{time()-start_time:.4f}sec.")
        return summary

    async def transcribe_and_summarize(self, unique_id: str, file: TempFile) -> TranscriptionData:
        if self.cache:
            cached = await self.cache.get(unique_id)
            if cached:
                logger.debug("Transcription obtained from cache")
                return cached

        transcribed_text = await self.transcribe_text(file)
        summary = self.calculate_summary(transcribed_text)
        data = TranscriptionData(
            transcription=transcribed_text,
            summary=summary,
            file_unique_id=unique_id,
            date_processed=datetime.now(),
        )
        if self.cache:
            await self.cache.store(unique_id, data)
            logger.debug("Transcription stored to cache")
        return data
