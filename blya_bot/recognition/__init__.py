from typing import Type

from .interface import MediaType, SpeechRecognizer, TempFile

_AVAILABLE_RECOGNIZERS = ["vosk", "whisper"]


def get_recognizer_by_name(name: str) -> Type[SpeechRecognizer]:
    # Here we importing recognizers in runtime, becuase "whisper" has some issues for loading model weights
    #   if "vosk" module already imported. Loading model causes "segmentation failure" crash.
    if name == "vosk":
        try:
            from .vosk import VoskSpeechRecognizer
        except ImportError:
            raise
        else:
            return VoskSpeechRecognizer

    elif name == "whisper":
        try:
            from .whisper import WhisperSpeechRecognizer
        except ImportError:
            raise
        else:
            return WhisperSpeechRecognizer

    else:
        raise Exception(f"Unknown recognizer name {name!r}, available recognizers: {', '.join(_AVAILABLE_RECOGNIZERS)}")


__all__ = (
    "MediaType",
    "SpeechRecognizer",
    "TempFile",
    # "VoskSpeechRecognizer",
    # "WhisperSpeechRecognizer",
    "get_recognizer_by_name",
)
