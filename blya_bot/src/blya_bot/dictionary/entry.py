from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DictEntryFlags:
    morphing: bool = True
    exclude: bool = False
    exact_match: bool = True

    def __repr__(self):

        def b(flag) -> str:
            if flag:
                return "1"
            return "0"

        s = f"<flags morph:{b(self.morphing)}|exclude:{b(self.exclude)}|exact:{b(self.exact_match)}>"
        return s

    def __hash__(self) -> int:
        return hash((self.morphing, self.exclude, self.exact_match))


@dataclass(slots=True, kw_only=True)
class DictEntry:
    word: str
    flags: DictEntryFlags
    parent: DictEntry | None = None

    def chain_str(self) -> str:
        if self.parent:
            return self.parent.chain_str() + " -> " + self.word
        return self.word

    def parent_root(self) -> DictEntry:
        if self.parent:
            return self.parent.parent_root()
        return self

    def __hash__(self) -> int:
        return hash((self.word, self.flags, self.parent))
