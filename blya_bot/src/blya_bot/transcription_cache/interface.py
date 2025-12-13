from abc import abstractmethod
from typing import Protocol

from blya_bot.models import TranscriptionData


class BaseTranscriptionCache(Protocol):
    @abstractmethod
    async def store(self, file_unique_id: str, transcription_data: TranscriptionData):
        pass

    @abstractmethod
    async def get(self, file_unique_id: str) -> TranscriptionData | None:
        pass

    async def setup(self):
        pass

    async def teardown(self):
        pass

    async def clean(self) -> int:
        """Remove expired entries from the cache. Returns number of deleted entries."""
        return 0


class NullTranscriptionCache(BaseTranscriptionCache):
    async def store(self, file_unique_id: str, transcription_data: TranscriptionData):
        pass

    async def get(self, file_unique_id: str) -> TranscriptionData | None:
        pass

    async def setup(self):
        pass

    async def teardown(self):
        pass

    async def clean(self) -> int:
        return 0
