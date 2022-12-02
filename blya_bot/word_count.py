from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from operator import itemgetter
from typing import Dict, Iterable, List

import structlog
from ahocorapy.keywordtree import KeywordTree

from .dictionary import normalize_text, parse_dictionary

logger = structlog.getLogger(__name__)


def build_keyword_tree_from_word_iter(it: Iterable[str]):
    kwtree = KeywordTree(case_insensitive=True)
    for word in it:
        kwtree.add(word.strip())
    kwtree.finalize()
    return kwtree


def keyword_tree_from_file(word_list_file: str, extend_by_morphing: bool = True) -> KeywordTree:
    with open(word_list_file, "r") as fp:
        logger.debug("Parsing dictionary...")
        words = parse_dictionary(fp.readlines(), extend_by_morphing)
        logger.debug("Assembling keyword tree...")
        kwtree = build_keyword_tree_from_word_iter(words)
        logger.debug("Keyword tree assembled")
        return kwtree


@dataclass
class TextSummary:
    counter: Counter
    markup: dict[tuple[int, int], str]


class _WordCounter:
    def __init__(self, kwtree: KeywordTree) -> None:
        self._kwtree = kwtree
        self._counts: Counter = Counter()
        self._markup: dict[tuple[int, int], str] = {}
        self._done = False

    def feed(self, text: str) -> None:
        if self._done:
            raise RuntimeError("Could not feed more, then 1 time")

        normalized_text = normalize_text(text)
        words_mapping: Dict[int, List[str]] = {}
        # Searching for all entries of words, stored in kwtree.
        for word, found_pos in self._kwtree.search_all(normalized_text):
            # Assembling dict where keys are pos and value - list of matches
            words_mapping.setdefault(found_pos, []).append(word)

        # Collecting statistics
        last_pos, last_word = 0, None
        for pos, words_same_pos in sorted(list(words_mapping.items()), key=itemgetter(0)):
            # Because kwtree already returns sorted values, last element from "words_same_pos" is longest
            longest_match = words_same_pos[-1]
            # If we match some other word previously, and it contains current longest match - ignore current match
            if (
                last_word
                and last_word.endswith(longest_match)
                and (pos - len(last_word.removesuffix(longest_match))) == last_pos
            ):
                continue
            self._counts[longest_match] += 1
            self._markup[
                (
                    pos,
                    pos + len(longest_match),
                )
            ] = longest_match
            last_pos, last_word = pos, longest_match
        self._done = True

    def summary(self) -> TextSummary:
        return TextSummary(
            counter=Counter({w: c for w, c in self._counts.items() if c > 0}), markup=self._markup.copy()
        )


class WordCounterEngine:
    @classmethod
    def from_file(cls, file_name: str) -> WordCounterEngine:
        return cls(keyword_tree_from_file(file_name))

    def __init__(self, keyword_tree: KeywordTree) -> None:
        self.kwtree = keyword_tree

    def calculate_summary(self, text) -> TextSummary:
        counter = _WordCounter(self.kwtree)
        counter.feed(text)
        return counter.summary()
