from collections import namedtuple, defaultdict
from typing import Optional, Tuple, Generator


Split = namedtuple("Split", "pos, sep")
Separator = namedtuple("Separator", "idx, value, length")


def highlight_text(text: str, markup: dict[tuple[int, int], str]) -> str:
    highlighted_text = ""
    prev_end = 0
    for (start, end), word in markup.items():
        highlighted_text += text[prev_end:start] + "<b>" + word.upper() + "</b>"
        prev_end = end
    return highlighted_text


def split_in_chunks(
    text: str, max_size: int, separators=("\n", " "), allow_no_sep_split=True
) -> Generator[str, None, None]:
    r"""
    >>> list(split_in_chunks("111\n222\n333 444 555 666.777.888.999.000", 7, ['\n', ' ', '.']))
    ['111\n222', '333 444', '555', '666.777', '888.999', '000']
    >>> list(split_in_chunks('1\n2\n3\n4\n5\n6\n7\n8\n9\n0', 3, ['\n', ' ']))
    ['1\n2', '3\n4', '5\n6', '7\n8', '9\n0']
    >>> list(split_in_chunks('Hello, how are you?', 6, ['\n', ' ']))
    ['Hello,', 'how', 'are', 'you?']
    >>> list(split_in_chunks('LooongStringWithoutSeparators', 10, ['\n', ' ']))
    ['LooongStri', 'ngWithoutS', 'eparators']
    >>> list(split_in_chunks('LooongStringWith Some Separators', 10, ['\n', ' ']))
    ['LooongStri', 'ngWith', 'Some', 'Separators']
    >>> list(split_in_chunks('1\n2\n\n\n3\n4\n5\n\n\n6\n7', 5, ['\n\n', '\n']))
    ['1\n2\n', '3\n4\n5', '\n6\n7']

    :param text:
    :param max_size:
    :param separators:
    :param allow_no_sep_split:
    :return:
    """
    separators = [Separator(idx, sep, len(sep)) for idx, sep in enumerate(separators)]
    max_sep_len = max(sep.length for sep in separators)

    def check_separator(text_part) -> Optional[Separator]:
        for sep in separators:
            if text_part[: len(sep)] == sep.value:
                return sep
        return None

    def try_split(current_text) -> Tuple[int, str]:
        available_spilt_points = defaultdict(list)

        for pos, char in enumerate(current_text):
            sep_found: Separator = check_separator(current_text[pos : pos + max_sep_len])
            if sep_found:
                available_spilt_points[sep_found.idx].append(Split(pos, sep_found))

            if pos + 1 > max_size:
                # Check available splits, prioritized by separators
                for sep in separators:
                    if len(splits_stored := available_spilt_points[sep.idx]):
                        # Choose last available split
                        split: Split = splits_stored[-1]
                        return split.pos + split.sep.length, current_text[: split.pos]
                else:
                    if allow_no_sep_split:
                        return pos, current_text[:pos]
                    raise ValueError(f"Oops! Text could not be properly split in chunks")
        else:
            return len(current_text) - 1, current_text

    while True:
        if len(text) <= max_size:
            yield text
            return
        offset, chunk = try_split(text)
        yield chunk
        text = text[offset:]
