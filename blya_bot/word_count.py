from collections import Counter
from typing import Dict, Iterator, List

from ahocorapy.keywordtree import KeywordTree


def count_words_total(text) -> int:
    return len(text.split())


def build_keyword_tree_from_word_iter(it: Iterator[str]):
    kwtree = KeywordTree(case_insensitive=True)
    for word in it:
        kwtree.add(word.strip())
    kwtree.finalize()
    return kwtree


def keyword_tree_from_file(word_list_file: str) -> KeywordTree:
    with open(word_list_file, "r") as fp:
        return build_keyword_tree_from_word_iter(fp)


class WordCounter:
    def __init__(self, kwtree: KeywordTree) -> None:
        self._kwtree = kwtree
        self._counts: Counter = Counter()

    def feed(self, text) -> None:
        words_mapping: Dict[int, List[str]] = {}
        # Searching for all entries of words, stored in kwtree.
        for word, found_pos in self._kwtree.search_all(text):
            # Assembling dict where keys are pos and value - list of matches
            words_mapping.setdefault(found_pos, []).append(word)

        # Collecting statistics
        last_word = None
        for words_same_pos in words_mapping.values():
            # Because kwtree already returns sorted values, last element from "words_same_pos" is longest
            longest_match = words_same_pos[-1]
            # If we match some other word previously, and it contains current longest match - ignore current match
            if last_word and last_word.endswith(longest_match):
                continue
            self._counts[longest_match] += 1
            last_word = longest_match

    def summary(self) -> Counter:
        return Counter({w: c for w, c in self._counts.items() if c > 0})
