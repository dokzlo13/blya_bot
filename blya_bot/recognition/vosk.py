import asyncio
import io
import json
import wave
from concurrent.futures import ThreadPoolExecutor
from typing import Generator

import structlog

from .interface import BaseSpeechRecognizer, TempFile
from .utils import async_wrap_iter

logger = structlog.getLogger(__name__)

try:
    import pydub
    import vosk
except ImportError:
    logger.error("'vosk' recognition core dependencies not installed")
    raise


async def convert_audio_async(input_buf: io.IOBase) -> io.BytesIO:
    loop = asyncio.get_event_loop()

    # Define the blocking task as a helper function
    def convert_audio(input_buf: io.IOBase) -> io.BytesIO:
        input_buf.seek(0)
        audio: pydub.AudioSegment = pydub.AudioSegment.from_file(input_buf)
        audio = audio.set_channels(1)
        audio = audio.set_sample_width(2)

        wav_buf = io.BytesIO()
        audio.export(format="wav", out_f=wav_buf)
        wav_buf.seek(0)
        return wav_buf

    # Run the blocking code in a separate thread
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, convert_audio, input_buf)


class VoskSpeechRecognizer(BaseSpeechRecognizer):
    def __init__(self, model: "vosk.Model") -> None:
        self.model = model

    @classmethod
    def from_options(cls, **options):
        model = vosk.Model(model_path=options.get("model_path"))
        return cls(model)

    def _recognize(self, wav_buf: io.IOBase) -> Generator[str, None, None]:
        # Loading as wave to obtain framerate for recognizer
        wf = wave.open(wav_buf, "rb")  # type: ignore

        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
            logger.warning("Audio file must be WAV format mono PCM.")

        rec = vosk.KaldiRecognizer(self.model, wf.getframerate())
        # rec.SetWords(True)
        # rec.SetPartialWords(True)
        # rec.SetNLSML(True)

        while True:
            data = wav_buf.read(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                yield result["text"] + " "

        final_result = json.loads(rec.FinalResult())
        yield final_result["text"]

        rec.Reset()
        del rec
        del wf

    async def recognize(self, file: TempFile) -> str:
        wav_buf = await convert_audio_async(file.file)  # type: ignore
        parts = [part async for part in async_wrap_iter(self._recognize(wav_buf))]
        return "".join(parts)
