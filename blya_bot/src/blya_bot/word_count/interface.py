from __future__ import annotations

from abc import abstractmethod
from typing import Protocol

from blya_bot.dictionary.entry import DictEntry
from blya_bot.models import TextSummary


class BaseWordCounter(Protocol):
    @classmethod
    @abstractmethod
    def from_dictionary(cls, dictionary: list[DictEntry]) -> "BaseWordCounter":
        pass

    @abstractmethod
    def calculate_summary(self, text: str) -> TextSummary:
        pass
