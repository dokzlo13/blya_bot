import json
from datetime import datetime, timedelta

import aiosqlite
import structlog

from blya_bot.models import TranscriptionData

from .interface import BaseTranscriptionCache

logger = structlog.getLogger(__name__)


class SqliteTranscriptionCache(BaseTranscriptionCache):
    def __init__(self, conn: aiosqlite.Connection, ttl: int | None = None) -> None:
        self.conn = conn
        self.conn.row_factory = aiosqlite.Row
        self._migrated = False
        self.ttl = ttl

    async def setup(self):
        if not self._migrated:
            await self.migrate()
            self._migrated = True

    async def teardown(self):
        await self.conn.close()

    async def migrate(self):
        async with self.conn.cursor() as cursor:
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS transcription_cache(
                file_unique_id TEXT PRIMARY KEY,
                transcription TEXT,
                summary TEXT,
                date_processed INTEGER
                )"""
            )

    @staticmethod
    def _data_as_params(data: TranscriptionData) -> tuple[str, str, str, int]:
        dict_data = data.as_dict()
        return (
            dict_data["file_unique_id"],
            dict_data["transcription"],
            json.dumps(dict_data["summary"]),
            dict_data["date_processed"],  # Timestamp as integer
        )

    @staticmethod
    def _parse_row_to_data(row) -> TranscriptionData:
        return TranscriptionData.from_dict(
            {
                "file_unique_id": row["file_unique_id"],
                "transcription": row["transcription"],
                "summary": json.loads(row["summary"]),
                "date_processed": row["date_processed"],  # Already an integer timestamp
            }
        )

    async def get(self, file_unique_id: str) -> TranscriptionData | None:
        async with self.conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM transcription_cache WHERE file_unique_id=?", (file_unique_id,))
            async for row in cursor:
                return self._parse_row_to_data(row)
        return None

    async def clean(self) -> int:
        """Remove expired entries from the cache. Returns number of deleted entries."""
        if self.ttl is None:
            return 0

        expiration_threshold = int((datetime.now() - timedelta(seconds=self.ttl)).timestamp())

        async with self.conn.cursor() as cursor:
            await cursor.execute("DELETE FROM transcription_cache WHERE date_processed <= ?", (expiration_threshold,))
            deleted_rows = cursor.rowcount

        await self.conn.commit()

        return deleted_rows

    async def store(self, file_unique_id: str, transcription_data: TranscriptionData):
        async with self.conn.cursor() as cursor:
            # Store the new transcription data
            await cursor.execute(
                "INSERT INTO transcription_cache VALUES (?, ?, ?, ?)", self._data_as_params(transcription_data)
            )
        await self.conn.commit()
