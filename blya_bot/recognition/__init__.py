from typing import Type

from .interface import BaseSpeechRecognizer, TempFile

AVAILABLE_RECOGNIZERS = ["vosk", "faster-whisper", "pywhispercpp"]


def get_recognizer_by_name(name: str) -> Type[BaseSpeechRecognizer]:
    # Here we importing recognizers in runtime, becuase "whisper" has some issues for loading model weights
    #   if "vosk" module already imported. Loading model causes "segmentation failure" crash.
    if name == "vosk":
        from .vosk import VoskSpeechRecognizer

        return VoskSpeechRecognizer

    elif name == "faster-whisper":
        from .faster_whisper import FastWhisperSpeechRecognizer

        return FastWhisperSpeechRecognizer

    elif name == "pywhispercpp":
        from .pywhispercpp import PyWhisperCppSpeechRecognizer

        return PyWhisperCppSpeechRecognizer

    else:
        raise Exception(f"Unknown recognizer name {name!r}, available recognizers: {', '.join(AVAILABLE_RECOGNIZERS)}")


__all__ = (
    "BaseSpeechRecognizer",
    "TempFile",
    "get_recognizer_by_name",
)
