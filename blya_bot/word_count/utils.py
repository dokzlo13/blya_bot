import string


def normalize_text(text: str) -> str:
    # return text.translate(str.maketrans("", "", string.punctuation)).lower().strip() \
    # .replace("ё", "е").replace("й", "и")
    return text.replace("ё", "е").replace("й", "и")


def count_words_total(text) -> int:
    return len(text.translate(str.maketrans("", "", string.punctuation)).lower().strip().split())


def is_whitespace_or_symbol(char):
    # Check if the character is a whitespace
    if char.isspace():
        return True
    # Check if the character is NOT a letter
    if not char.isalpha():
        return True
    return False
