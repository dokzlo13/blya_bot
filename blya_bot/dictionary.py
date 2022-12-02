import re
import string
import warnings
from itertools import product

import structlog

# TODO: Another languages
try:
    import pymorphy2
    import pymorphy2_dicts_ru

    morph = pymorphy2.MorphAnalyzer(path=pymorphy2_dicts_ru.get_path())

except ImportError:
    warnings.warn("Morphological extension is not available, install 'pymorphy2' and 'pymorphy2-dicts-ru'")
    morph = None


logger = structlog.getLogger(__name__)

VARIANTS_REGEX = re.compile(
    r"(\[(?P<variants_1>[^\]]*)\]|\{(?P<variants_2>[^\}]*)\})", flags=re.UNICODE | re.IGNORECASE
)


def parse_group(group: str) -> tuple[str, ...]:
    parsed_group = tuple(v.strip() for v in group[1:-1].split("|"))
    if group[0] == "{":
        return parsed_group
    else:
        return ("",) + parsed_group


def split_in_groups(word):
    groups: list[tuple[str, ...]] = []
    last_pos = 0
    matches = list(VARIANTS_REGEX.finditer(word))
    if not len(matches):
        groups.append((word,))
    else:
        for match in matches:
            start, end = match.span(0)
            if start == 0:
                groups.append(parse_group(match.group()))
            else:
                groups.append((word[last_pos:start],))
                groups.append(parse_group(match.group()))
            last_pos = end
        groups.append((word[last_pos:],))
    return groups


def product_variants(word: str) -> set[str]:
    return set("".join(parts) for parts in product(*split_in_groups(word)))


def parse_dictionary(rows: list[str], extend_by_morphing: bool = True) -> list[str]:
    all_words: set[str] = set()
    exclude_words: set[str] = set()

    raw_words_read = 0

    for raw_word in rows:
        word = raw_word.strip().lower()
        if not word or word.startswith("#"):
            continue

        raw_words_read += 1

        use_morph_this_word = extend_by_morphing
        if "!" in word:
            word = word.replace("!", "")
            use_morph_this_word = False

        if word.startswith("~"):
            temp_words = product_variants(word.replace("~", ""))
            if use_morph_this_word:
                exclude_words.update(product_morphs(temp_words))
            else:
                exclude_words.update(temp_words)
        else:
            temp_words = product_variants(word)
            if use_morph_this_word:
                all_words.update(product_morphs(temp_words))
            else:
                all_words.update(temp_words)

    done_dict = sorted(list(all_words - exclude_words))
    logger.info("Dictionary generated", raw_words=raw_words_read, final_dict=len(done_dict))
    return done_dict


def get_all_morphs(word: str) -> set[str]:
    if morph is None:
        return {word}

    words_set: set[str] = set()
    words_set.add(word)
    for variant in morph.parse(word):
        for inflect in variant.lexeme:
            dict_word = normalize_text(inflect.word)
            if len(dict_word) > 2:
                words_set.add(dict_word)
    return words_set


def product_morphs(words: set[str]) -> set[str]:
    words_set: set[str] = set()
    for word in words:
        words_set.update(get_all_morphs(word))
    return words_set


def count_words_total(text) -> int:
    return len(text.translate(str.maketrans("", "", string.punctuation)).lower().strip().split())


def normalize_text(text: str) -> str:
    # return text.translate(str.maketrans("", "", string.punctuation)).lower().strip().replace("ё", "е").replace("й", "и")
    return text.replace("ё", "е").replace("й", "и")
