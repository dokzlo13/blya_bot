import structlog

from .interface import MediaType, SpeechRecognizer, TempFile

logger = structlog.getLogger(__name__)


try:
    import whisper
except ImportError:
    logger.warning("'whisper' recognition core dependencies not installed")
    whisper = None


class WhisperSpeechRecognizer(SpeechRecognizer):
    def __init__(self, whisper_model, lang: str) -> None:
        self.model = whisper_model
        self.lang = lang

    @classmethod
    def from_options(cls, **options):
        logger.info("Loading whisper model", options=options)
        model = whisper.load_model(
            name=options.get("model_name", "tiny"),
            download_root=options.get("download_root", None),
            in_memory=options.get("in_memory", False),
            device=options.get("device", "cuda"),
        )
        logger.info("Whisper model loaded")
        return cls(model, lang=options.get("language", "ru"))

    async def recognize(self, file: TempFile, media_type: MediaType) -> str:
        audio = whisper.load_audio(file.name)
        # # make log-Mel spectrogram and move to the same device as the model
        # mel = whisper.log_mel_spectrogram(audio).to(self.model.device)

        # # detect the spoken language
        # _, probs = self.model.detect_language(mel)
        # used_lang = max(probs, key=probs.get)
        # logger.debug("Language detected", lang=used_lang, match=probs[used_lang])

        # # decode the audio
        # options = whisper.DecodingOptions(language=used_lang)
        # result = whisper.decode(self.model, mel, options)
        # print(result.text)

        result = whisper.transcribe(
            self.model,
            audio,
            verbose=None,
            language=self.lang,
            no_speech_threshold=None,
            logprob_threshold=None,
        )
        return result["text"].strip()
