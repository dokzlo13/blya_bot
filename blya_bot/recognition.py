import io
import json
import wave
from typing import AsyncGenerator, Generator

import vosk

from .tools import async_wrap_iter


class SpeechRecognizer:
    def __init__(self, recognition_model: vosk.Model) -> None:
        self.recognition_model = recognition_model

    def _recognize(self, wav_buf: io.IOBase) -> Generator[str, None, None]:
        # Loading as wave to obtain framerate for recognizer
        wf = wave.open(wav_buf, "rb")  # type: ignore

        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
            print("Audio file must be WAV format mono PCM.")

        rec = vosk.KaldiRecognizer(self.recognition_model, wf.getframerate())
        # rec.SetWords(True)
        rec.SetPartialWords(True)
        rec.SetNLSML(True)

        while True:
            data = wav_buf.read(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                yield result["text"] + " "

        final_result = json.loads(rec.FinalResult())
        yield final_result["text"]

    def recognize(self, wav_buf: io.IOBase) -> AsyncGenerator[str, None]:
        return async_wrap_iter(self._recognize(wav_buf))
