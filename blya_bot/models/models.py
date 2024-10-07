from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any

Markup = list[tuple[tuple[int, int], str]]


@dataclass(slots=True)
class TextSummary:
    counter: Counter
    markup: Markup

    def as_dict(self) -> dict[str, Any]:
        return {
            "counter": dict(self.counter),
            "markup": self.markup,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TextSummary:
        return cls(counter=Counter(data["counter"]), markup=data["markup"])


@dataclass(slots=True)
class TranscriptionData:
    file_unique_id: str
    transcription: str
    summary: TextSummary
    date_processed: datetime

    def as_dict(self) -> dict[str, Any]:
        return {
            "file_unique_id": self.file_unique_id,
            "transcription": self.transcription,
            "summary": self.summary.as_dict(),
            "date_processed": int(self.date_processed.timestamp()),  # Store as timestamp
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TranscriptionData:
        return TranscriptionData(
            transcription=data["transcription"],
            summary=TextSummary.from_dict(data["summary"]),
            file_unique_id=data["file_unique_id"],
            date_processed=datetime.fromtimestamp(data["date_processed"]),  # Convert timestamp to datetime
        )
