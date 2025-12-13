import asyncio
import io
import json
import wave
from collections.abc import Generator

import structlog

from .interface import BaseSpeechRecognizer, TempFile
from .utils import async_wrap_iter

logger = structlog.getLogger(__name__)

try:
    import vosk
except ImportError:
    logger.error("'vosk' recognition core dependencies not installed")
    raise


async def convert_audio_async(input_buf: io.IOBase) -> io.BytesIO:
    """Convert audio to mono 16-bit WAV format using ffmpeg.

    Args:
        input_buf: Input audio buffer in any format supported by ffmpeg.

    Returns:
        BytesIO buffer containing WAV audio data.

    Raises:
        RuntimeError: If ffmpeg conversion fails.
    """
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-i", "pipe:0",        # Read from stdin
        "-ac", "1",            # Mono channel
        "-ar", "16000",        # 16kHz sample rate (standard for speech recognition)
        "-sample_fmt", "s16",  # 16-bit signed
        "-f", "wav",           # Output format
        "pipe:1",              # Write to stdout
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    input_buf.seek(0)
    stdout, stderr = await proc.communicate(input_buf.read())

    if proc.returncode != 0:
        error_msg = stderr.decode() if stderr else "Unknown error"
        logger.error("ffmpeg conversion failed", returncode=proc.returncode, stderr=error_msg)
        raise RuntimeError(f"ffmpeg conversion failed: {error_msg}")

    return io.BytesIO(stdout)


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
