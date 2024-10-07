from abc import abstractmethod
from pathlib import Path
from typing import Protocol

from .entry import DictEntry


class IDictionaryLoader(Protocol):
    @abstractmethod
    def load(self, file_path: Path) -> list[DictEntry]:
        pass


class IDictionaryModifier(Protocol):
    @abstractmethod
    def modify_dict(self, dictionary: list[DictEntry]) -> list[DictEntry]:
        pass
