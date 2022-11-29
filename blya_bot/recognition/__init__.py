from typing import Type

from .interface import MediaType, SpeechRecognizer, TempFile
from .vosk import VoskSpeechRecognizer
from .whisper import WhisperSpeechRecognizer

_AVAILABLE_RECOGNIZERS = {
    "whisper": WhisperSpeechRecognizer,
    "vosk": VoskSpeechRecognizer,
}


def get_recognizer_by_name(name: str) -> Type[SpeechRecognizer]:
    recognizer = _AVAILABLE_RECOGNIZERS[name]
    if recognizer is None:
        raise Exception(f"Unknown recognizer name {name!r}, available: {', '.join(_AVAILABLE_RECOGNIZERS)}")
    return recognizer  # type: ignore


__all__ = (
    "MediaType",
    "SpeechRecognizer",
    "TempFile",
    "VoskSpeechRecognizer",
    "WhisperSpeechRecognizer",
    "get_recognizer_by_name",
)
