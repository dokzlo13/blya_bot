import aiosqlite
import json
from blya_bot.models import TranscriptionData
from .interface import BaseTranscriptionCache


class SqliteTranscriptionCache(BaseTranscriptionCache):
    def __init__(self, conn: aiosqlite.Connection) -> None:
        self.conn = conn
        self.conn.row_factory = aiosqlite.Row
        self._migrated = False

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
                date_processed TEXT
                )"""
            )

    @staticmethod
    def _data_as_params(data: TranscriptionData) -> tuple[str, str, str, str]:
        dict_data = data.as_dict()
        return (
            dict_data["file_unique_id"],
            dict_data["transcription"],
            json.dumps(dict_data["summary"]),
            dict_data["date_processed"],
        )

    @staticmethod
    def _parse_row_to_data(row) -> TranscriptionData:
        return TranscriptionData.from_dict(
            {
                "file_unique_id": row["file_unique_id"],
                "transcription": row["transcription"],
                "summary": json.loads(row["summary"]),
                "date_processed": row["date_processed"],
            }
        )

    async def get(self, file_unique_id: str) -> TranscriptionData | None:
        async with self.conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM transcription_cache WHERE file_unique_id=?", (file_unique_id,))
            async for row in cursor:
                return self._parse_row_to_data(row)
        return None

    async def store(self, file_unique_id: str, transcription_data: TranscriptionData):
        async with self.conn.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO transcription_cache VALUES (?, ?, ?, ?)", self._data_as_params(transcription_data)
            )
        await self.conn.commit()
