from __future__ import annotations

import asyncio
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import structlog

from .interface import BaseSpeechRecognizer, TempFile
from .utils import async_wrap_iter

logger = structlog.getLogger(__name__)


try:
    from faster_whisper import WhisperModel
except (ImportError, ModuleNotFoundError):
    logger.error("'faster_whisper' recognition core dependencies not installed")
    raise


class FastWhisperSpeechRecognizer(BaseSpeechRecognizer):
    def __init__(self, whisper_model: "WhisperModel", lang: str, beam_size: int = 5) -> None:
        self.model = whisper_model
        self.lang = lang
        self.beam_size = beam_size

    @classmethod
    def from_options(cls, **options) -> FastWhisperSpeechRecognizer:
        logger.info("Loading whisper model", options=options)
        model = WhisperModel(
            model_size_or_path=options["model"],
            device=options.get("device", "auto"),
            compute_type=options.get("compute_type", None),
        )
        logger.info("Whisper model loaded")
        return cls(model, lang=options.get("language", None))

    async def recognize(self, file: TempFile) -> str:
        segments, info = self.model.transcribe(
            file.name,
            language=self.lang,
            no_speech_threshold=None,
            beam_size=self.beam_size,
        )
        text = ""
        logger.debug(
            "Transcription info",
            transcription_options=info.transcription_options,
            language=info.language,
            language_probability=info.language_probability,
            duration=info.duration,
            duration_after_vad=info.duration_after_vad,
        )

        # Convert the sync generator to an async one
        async for seg in async_wrap_iter(segments):
            text += seg.text
            await asyncio.sleep(0)  # This will make the task cooperative
        return text
