from collections import Counter
from typing import Dict, List

from ahocorapy.keywordtree import KeywordTree


def count_words_total(text) -> int:
    return len(text.split())


def build_keyword_tree(word_list_file: str) -> KeywordTree:
    kwtree = KeywordTree(case_insensitive=True)
    with open(word_list_file, "r") as fp:
        for word in fp:
            kwtree.add(word.strip())
    kwtree.finalize()
    return kwtree


class WordCounter:
    def __init__(self, kwtree: KeywordTree) -> None:
        self._kwtree = kwtree
        self._counts: Counter = Counter()

    def feed(self, text) -> None:
        words_mapping: Dict[int, List[str]] = {}
        # Searching for all entries of words, stored in kwtree
        for word, pos in self._kwtree.search_all(text):
            words_mapping.setdefault(pos, []).append(word)

        # Collecting statistics
        for words_same_pos in words_mapping.values():
            # Because kwtree already returns sorted values, last element from "words_same_pos" is longest
            self._counts[words_same_pos[-1]] += 1

    def summary(self) -> Counter:
        return Counter({w: c for w, c in self._counts.items() if c > 0})
