from pathlib import Path
from pprint import pprint
from typing import Any

import pymorphy3
import pymorphy3_dicts_ru
import pympler
from ahocorasick_rs import AhoCorasick, Implementation, MatchKind
from pympler import asizeof

from blya_bot.dictionary.dict_v2 import (
    DictEntry,
    MorphyDict,
)
from blya_bot.dictionary.sparse_list import SparseList


def human_readable_size(bytes_size):
    # List of size units
    units = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
    # Convert bytes_size to a float for precision in calculations
    size = float(bytes_size)

    # Iterate over the units
    for unit in units:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024

    # If the size exceeds the largest unit, it will return in YB (Yottabytes)
    return f"{size:.2f} YB"


def sizeof(obj):
    return human_readable_size(asizeof.asizeof(obj))


# dictionary = MorphyDict(char_equality=[("е", "ё"), ("и", "й")]).load(Path("./trash/dict_test.txt"))
dictionary = MorphyDict(char_equality=[("е", "ё"), ("и", "й")]).load(Path("./fixtures/bad_words.txt"))



# pprint(dictionary)

morph = pymorphy3.MorphAnalyzer(path=pymorphy3_dicts_ru.get_path())

def expand_with_pymorphy(dictionary: list[DictEntry]) -> list[DictEntry]:
    ext_dictionary = []
    for entry in dictionary:
        if not entry.flags.morphing:
            ext_dictionary.append(entry)
            continue

        words_dedup = set()
        words_dedup.add(entry.word)
        for variant in morph.parse(entry.word):
            for inflect in variant.lexeme:
                words_dedup.add(inflect.word)

        for word in words_dedup:
            if word == entry.word:
                ext_dictionary.append(entry)
                continue

            ext_dictionary.append(DictEntry(word=word, flags=entry.flags, parent=entry))

    return list(set(ext_dictionary))


dictionary_ext = expand_with_pymorphy(dictionary)

# pprint(dictionary_ext)

# print(len(dictionary_ext))
print("unoptimized:", sizeof(dictionary_ext), len(dictionary_ext))

print("-" * 200)


def as_sparse_list(dictionary: list[DictEntry]) -> SparseList[DictEntry]:
    flat_entries_list = SparseList[DictEntry]()

    if not dictionary:
        return flat_entries_list  # Handle the case of an empty list

    flat_cntr = 1  # Start with 1 since we count the first entry
    current_parent_root = dictionary[0].parent_root()

    for idx, entry in enumerate(dictionary[1:], start=1):  # Start from the second element
        new_parent_root = entry.parent_root()

        if new_parent_root.word == current_parent_root.word:
            flat_cntr += 1
            continue

        # Add the range for the previous root
        flat_entries_list.add(idx - flat_cntr, idx, current_parent_root)
        flat_cntr = 1
        current_parent_root = new_parent_root

    # Add the last range after the loop
    flat_entries_list.add(len(dictionary) - flat_cntr, len(dictionary), current_parent_root)

    return flat_entries_list


# print("-" * 200)
# sparse_list = as_sparse_list(dictionary_ext)
# print("optimized:", sizeof(sparse_list))

pprint(dictionary_ext)

ac = AhoCorasick(
    [e.word for e in dictionary_ext], matchkind=MatchKind.LeftmostLongest, implementation=Implementation.ContiguousNFA
)


print("TRANSCRIBING!")

from faster_whisper import WhisperModel

# model = WhisperModel("small", device="cpu", compute_type="int8")
model = WhisperModel("tiny", device="cpu", compute_type="int8")
# model = WhisperModel("medium", device="cpu", compute_type="float32")

# segments, info = model.transcribe("./trash/audio_2024-09-17_23-02-56.ogg")
segments, info = model.transcribe("./trash/audio_2024-09-18_14-16-17.ogg")
# segments, info = model.transcribe("./trash/audio_2024-09-17_22-58-40.ogg", task="translate")
text = ""
for seg in segments:
    text += seg.text


print(text)


def is_whitespace_or_symbol(char):
    # Check if the character is a whitespace
    if char.isspace():
        return True
    # Check if the character is NOT a letter
    if not char.isalpha():
        return True
    return False


for word_idx, start, end in ac.find_matches_as_indexes(text.lower()):
    entry = dictionary_ext[word_idx]
    print(repr(text[start - 1 : end + 1]), entry.flags, repr(entry.chain_str()))
    if entry.flags.exact_match and start != 0 and not is_whitespace_or_symbol(text[start - 1]):
        print("EXCLUDE!", entry)
        continue
