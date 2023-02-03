import re
from itertools import product

import structlog

from .interface import BaseDictionaryLoader

logger = structlog.getLogger(__name__)

VARIANTS_REGEX = re.compile(
    r"(\[(?P<variants_1>[^\]]*)\]|\{(?P<variants_2>[^\}]*)\})", flags=re.UNICODE | re.IGNORECASE
)


class DslDictLoader(BaseDictionaryLoader):
    @staticmethod
    def normalize_text(text: str) -> str:
        return text.replace("ё", "е").replace("й", "и")

    def load_dictionary(self, file: str) -> list[str]:
        with open(file, "r") as fp:
            logger.debug("Parsing dictionary...")
            words = self.parse_dictionary(fp.readlines())
            logger.debug("Dict loaded")
            return words

    @staticmethod
    def parse_group(group: str) -> tuple[str, ...]:
        parsed_group = tuple(v.strip() for v in group[1:-1].split("|"))
        if group[0] == "{":
            return parsed_group
        else:
            return ("",) + parsed_group

    def split_in_groups(self, word):
        groups: list[tuple[str, ...]] = []
        last_pos = 0
        matches = list(VARIANTS_REGEX.finditer(word))
        if not len(matches):
            groups.append((word,))
        else:
            for match in matches:
                start, end = match.span(0)
                if start == 0:
                    groups.append(self.parse_group(match.group()))
                else:
                    groups.append((word[last_pos:start],))
                    groups.append(self.parse_group(match.group()))
                last_pos = end
            groups.append((word[last_pos:],))
        return groups

    def product_variants(self, word: str) -> set[str]:
        return set("".join(parts) for parts in product(*self.split_in_groups(word)))

    def parse_dictionary(self, rows: list[str]) -> list[str]:
        all_words: set[str] = set()
        exclude_words: set[str] = set()

        raw_words_read = 0

        for raw_word in rows:
            word = raw_word.strip().lower()
            if not word or word.startswith("#"):
                continue

            raw_words_read += 1
            # Just support the syntax of dict
            if "!" in word:
                word = word.replace("!", "")

            if word.startswith("~"):
                temp_words = self.product_variants(word.replace("~", ""))
                exclude_words.update(temp_words)

            else:
                temp_words = self.product_variants(word)
                all_words.update(temp_words)

        done_dict = sorted(list(all_words - exclude_words))
        logger.info("Dictionary generated", raw_words=raw_words_read, final_dict=len(done_dict))
        return done_dict
