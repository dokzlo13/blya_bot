from abc import abstractmethod
from enum import Enum, auto
from tempfile import _TemporaryFileWrapper as TempFile
from typing import Protocol


class MediaType(Enum):
    VOICE = auto()
    VIDEO_NOTE = auto()


class SpeechRecognizer(Protocol):
    @classmethod
    @abstractmethod
    def from_options(cls, **options):
        pass

    @abstractmethod
    async def recognize(self, file: TempFile, media_type: MediaType) -> str:
        pass
