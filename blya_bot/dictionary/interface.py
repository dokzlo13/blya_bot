from abc import abstractmethod
from typing import Protocol


class BaseDictionaryLoader(Protocol):
    @abstractmethod
    def load_dictionary(self, file: str) -> list[str]:
        pass
