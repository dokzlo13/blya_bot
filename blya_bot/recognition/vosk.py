import asyncio
import io
import json
import threading
import wave
from typing import Generator

import structlog

from .interface import MediaType, SpeechRecognizer, TempFile

logger = structlog.getLogger(__name__)

try:
    import pydub
    import vosk
except ImportError:
    logger.warning("'vosk' recognition core dependencies not installed")
    pydub = None
    vosk = None


# TODO: make converter really async
def convert_audio(input_buf: io.IOBase, format: str) -> io.BytesIO:
    input_buf.seek(0)
    audio: pydub.AudioSegment = pydub.AudioSegment.from_file(input_buf, format=format)
    audio = audio.set_channels(1)
    audio = audio.set_sample_width(2)

    wav_buf = io.BytesIO()
    audio.export(format="wav", out_f=wav_buf)
    wav_buf.seek(0)
    return wav_buf


def async_wrap_iter(it):
    """Wrap blocking iterator into an asynchronous one"""
    loop = asyncio.get_event_loop()
    q = asyncio.Queue(1)
    exception = None
    _END = object()

    async def yield_queue_items():
        while True:
            next_item = await q.get()
            if next_item is _END:
                break
            yield next_item
        if exception is not None:
            # the iterator has raised, propagate the exception
            raise exception

    def iter_to_queue():
        nonlocal exception
        try:
            for item in it:
                # This runs outside the event loop thread, so we
                # must use thread-safe API to talk to the queue.
                asyncio.run_coroutine_threadsafe(q.put(item), loop).result()
        except Exception as e:
            exception = e
        finally:
            asyncio.run_coroutine_threadsafe(q.put(_END), loop).result()

    threading.Thread(target=iter_to_queue).start()
    return yield_queue_items()


class VoskSpeechRecognizer(SpeechRecognizer):
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

    async def recognize(self, file: TempFile, media_type: MediaType) -> str:
        format_map = {
            MediaType.VIDEO_NOTE: "mp4",
            MediaType.VOICE: "ogg",
        }
        wav_buf = convert_audio(file.file, format_map[media_type])  # type: ignore
        parts = [part async for part in async_wrap_iter(self._recognize(wav_buf))]
        return "".join(parts)
