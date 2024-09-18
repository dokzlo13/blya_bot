from __future__ import annotations

import structlog

from .interface import BaseSpeechRecognizer, TempFile

logger = structlog.getLogger(__name__)


try:
    from faster_whisper import WhisperModel
except (ImportError, ModuleNotFoundError):
    logger.error("'faster_whisper' recognition core dependencies not installed")
    raise


class FastWhisperSpeechRecognizer(BaseSpeechRecognizer):
    def __init__(self, whisper_model: "WhisperModel", lang: str) -> None:
        self.model = whisper_model
        self.lang = lang

    @classmethod
    def from_options(cls, **options) -> FastWhisperSpeechRecognizer:
        logger.info("Loading whisper model", options=options)
        model = WhisperModel(
            model_size_or_path=options["model_name"],
            device=options.get("device", "auto"),
        )
        logger.info("Whisper model loaded")
        return cls(model, lang=options.get("language", None))

    async def recognize(self, file: TempFile) -> str:
        segments, info = self.model.transcribe(
            file.name,
            language=self.lang,
            no_speech_threshold=None,
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
        for seg in segments:
            text += seg.text
        return text
