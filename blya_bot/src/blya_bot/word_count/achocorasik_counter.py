from __future__ import annotations

from collections import Counter
from operator import itemgetter
from typing import Dict, List

import structlog
from ahocorasick_rs import AhoCorasick, Implementation, MatchKind

from blya_bot.dictionary.entry import DictEntry
from blya_bot.models import TextSummary

from .interface import BaseWordCounter
from .utils import is_whitespace_or_symbol, normalize_text

logger = structlog.getLogger(__name__)


class AhoCorasickWordCounter(BaseWordCounter):
    def __init__(self, dictionary: list[DictEntry]) -> None:
        self.ac = AhoCorasick(
            [e.word for e in dictionary],
            matchkind=MatchKind.LeftmostLongest,
            implementation=Implementation.ContiguousNFA,
        )
        self.dictionary = dictionary

    @classmethod
    def from_dictionary(cls, dictionary: list[DictEntry]) -> AhoCorasickWordCounter:
        return cls(dictionary)

    def calculate_summary(self, text) -> TextSummary:
        counter = Counter()
        markup: list[tuple[tuple[int, int], str]] = []

        for word_idx, start, end in self.ac.find_matches_as_indexes(text.lower()):
            entry = self.dictionary[word_idx]
            word = text[start:end]

            logger.debug(f"Word {word!r} detected, source: {entry.chain_str()!r}")
            if entry.flags.exact_match:
                if start != 0 and not is_whitespace_or_symbol(text[start - 1]):
                    continue
                if end != len(text) and not is_whitespace_or_symbol(text[end]):
                    continue

            counter[word] += 1
            markup.append(((start, end), word))

        return TextSummary(counter=counter, markup=markup)
