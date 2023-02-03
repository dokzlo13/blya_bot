from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any


def flat_keys(mapping):
    return [{"key": k, "value": v} for k, v in mapping.items()]


def deflat_keys(arr):
    return {tuple(dct["key"]): dct["value"] for dct in arr}


@dataclass(slots=True)
class TextSummary:
    counter: Counter
    markup: dict[tuple[int, int], str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "counter": dict(self.counter),
            "markup": flat_keys(self.markup),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TextSummary:
        return cls(counter=Counter(data["counter"]), markup=deflat_keys(data["markup"]))


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
            "date_processed": self.date_processed.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TranscriptionData:
        return TranscriptionData(
            transcription=data["transcription"],
            summary=TextSummary.from_dict(data["summary"]),
            file_unique_id=data["file_unique_id"],
            date_processed=datetime.fromisoformat(data["date_processed"]),
        )
