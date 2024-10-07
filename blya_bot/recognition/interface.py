from __future__ import annotations

from abc import abstractmethod
from tempfile import _TemporaryFileWrapper as TempFile
from typing import Protocol


class BaseSpeechRecognizer(Protocol):
    @classmethod
    @abstractmethod
    def from_options(cls, **options) -> BaseSpeechRecognizer:
        pass

    @abstractmethod
    async def recognize(self, file: TempFile) -> str:
        pass
