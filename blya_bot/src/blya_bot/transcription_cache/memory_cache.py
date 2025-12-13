from __future__ import annotations

from time import time

import structlog

from blya_bot.models import TranscriptionData

from .interface import BaseTranscriptionCache

logger = structlog.getLogger(__name__)


class InMemoryTranscriptionCache(BaseTranscriptionCache):
    def __init__(self, ttl: int = 60 * 60) -> None:
        self._cache: dict[str, TranscriptionData] = {}
        self._expiration: dict[str, float] = {}
        self._ttl = ttl

    def _pop(self, key: str) -> TranscriptionData | None:
        value = self._cache.pop(key, None)  # type: ignore
        self._expiration.pop(key, None)
        return value

    async def store(self, file_unique_id: str, transcription_data: TranscriptionData):
        await self.clean()

        if file_unique_id in self._cache:
            self._pop(file_unique_id)

        self._cache[file_unique_id] = transcription_data
        self._expiration[file_unique_id] = time() + self._ttl

    async def get(self, file_unique_id: str) -> TranscriptionData | None:
        await self.clean()

        return self._cache.get(file_unique_id, None)

    async def clean(self) -> int:
        expired_keys = []
        current_time = time()
        for key, expiration_time in self._expiration.items():
            if current_time > expiration_time:
                expired_keys.append(key)

        for key in expired_keys:
            self._cache.pop(key, None)  # type: ignore
            self._expiration.pop(key, None)

        return len(expired_keys)

    async def setup(self):
        pass

    async def teardown(self):
        pass
