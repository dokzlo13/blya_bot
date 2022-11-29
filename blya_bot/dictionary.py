import re
import string
import warnings
from itertools import product

VARIANTS_REGEX = re.compile(
    r"(\[(?P<variants_1>[^\]]*)\]|\{(?P<variants_2>[^\}]*)\})", flags=re.UNICODE | re.IGNORECASE
)


def parse_group(group: str) -> tuple[str, ...]:
    parsed_group = tuple(v.strip() for v in group[1:-1].split("|"))
    if group[0] == "{":
        return parsed_group
    else:
        return ("",) + parsed_group


def multi_bracket(expr=r"\w+"):
    return r"(\[(?P<variants_1>[^\]]+)\]|\{(?P<variants_2>[^\}]+)\})"


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


def parse_dictionary(rows: list[str]) -> list[str]:
    all_words = []
    for raw_word in rows:
        word = raw_word.strip().lower()
        if not word or word.startswith("#"):
            continue
        all_words.extend(list("".join(parts) for parts in product(*split_in_groups(word))))
    return all_words


def get_all_morphs(words: list[str]) -> list[str]:
    try:
        import pymorphy2
        import pymorphy2_dicts_ru
    except ImportError:
        warnings.warn("Morphological extension is not available, install 'pymorphy2'")
        return words
    morph = pymorphy2.MorphAnalyzer(path=pymorphy2_dicts_ru.get_path())

    words_set: set[str] = set()
    for word in words:
        if "!" in word:
            words_set.add(word.replace("!", ""))
            continue

        words_set.add(word)
        for variant in morph.parse(word):
            for inflect in variant.lexeme:
                dict_word = normalize_text(inflect.word)
                if len(dict_word) > 2:
                    words_set.add(dict_word)
    return sorted(list(words_set))


def count_words_total(text) -> int:
    return len(text.translate(str.maketrans("", "", string.punctuation)).lower().strip().split())


def normalize_text(text: str) -> str:
    # return text.translate(str.maketrans("", "", string.punctuation)).lower().strip().replace("ё", "е").replace("й", "и")
    return text.replace("ё", "е").replace("й", "и")
