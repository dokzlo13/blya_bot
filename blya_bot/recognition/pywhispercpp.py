from __future__ import annotations

import asyncio
import re
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import suppress

import structlog

from .interface import BaseSpeechRecognizer, TempFile

logger = structlog.getLogger(__name__)


try:
    from pywhispercpp.model import Model, Segment
except (ImportError, ModuleNotFoundError):
    logger.error("'pywhispercpp' recognition core dependencies not installed")
    raise


def add_space_after_punctuation(text):
    # This regex looks for punctuation followed directly by a letter or digit
    result = re.sub(r"([.,!?])(\w)", r"\1 \2", text)
    # Remove any double spaces that might appear
    result = re.sub(r"\s+", " ", result)
    return result.strip()


class PyWhisperCppSpeechRecognizer(BaseSpeechRecognizer):
    def __init__(self, model: "Model", lang: str) -> None:
        self.model = model
        self.lang = lang

    @classmethod
    def from_options(cls, **options) -> PyWhisperCppSpeechRecognizer:
        logger.info("Loading whisper model", options=options)
        model = Model(
            model=options["model"],
            models_dir=options.get("models_dir", None),
            params_sampling_strategy=options.get("params_sampling_strategy", 0),
        )
        logger.info("Whisper model loaded")
        return cls(model, lang=options.get("language", None))

    async def recognize(self, file: TempFile) -> str:
        # Define a sentinel value that will be used to signal the end of transcription
        SENTINEL = object()

        # Define an asyncio queue to receive the segments asynchronously
        queue: asyncio.Queue[Segment | object] = asyncio.Queue()

        # Define the callback that will be used to push segments into the queue
        def callback(segments):
            for seg in segments:
                # Push segments into the queue asynchronously but from the main thread
                queue.put_nowait(seg)

        def transcribe_sync():
            logger.debug("Transcription started")
            self.model.transcribe(file.name, language=self.lang, new_segment_callback=callback, n_processors=None)
            # After transcription finishes, put the sentinel in the queue to indicate completion
            queue.put_nowait(SENTINEL)

        text = ""
        # Use ProcessPoolExecutor to run the transcribe method in a separate process
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            transcribe_future = loop.run_in_executor(pool, transcribe_sync)

            # Process segments asynchronously from the queue
            while True:
                # Use await to consume each segment from the queue as they are added by the callback
                with suppress(asyncio.TimeoutError):
                    # segment = await asyncio.wait_for(queue.get(), 5.0)
                    segment = await queue.get()
                    logger.debug(f"Segment transcribed: {segment}")
                    if segment is SENTINEL:  # Sentinel value to signify the end of transcription
                        break
                    # Append segment text to the result
                    text += segment.text + " "  # type: ignore

            # Wait for the transcription to finish in the separate process
            await transcribe_future

        return add_space_after_punctuation(text)
