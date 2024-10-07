import warnings

import structlog

from .entry import DictEntry
from .interface import IDictionaryModifier

logger = structlog.getLogger(__name__)


class PyMorphyRuDictModifier(IDictionaryModifier):
    def __init__(self, morph=None) -> None:
        if morph:
            self.morph = morph
        else:
            try:
                import pymorphy3
                import pymorphy3_dicts_ru

                self.morph = pymorphy3.MorphAnalyzer(path=pymorphy3_dicts_ru.get_path())

            except ImportError:
                warnings.warn("Morphological extension is not available, install 'pymorphy3' and 'pymorphy3-dicts-ru'")
                raise

    def modify_dict(self, dictionary: list[DictEntry]) -> list[DictEntry]:
        ext_dictionary = []
        for entry in dictionary:
            if not entry.flags.morphing:
                ext_dictionary.append(entry)
                continue

            words_dedup = set()
            words_dedup.add(entry.word)
            for variant in self.morph.parse(entry.word):
                for inflect in variant.lexeme:
                    if len(inflect.word) > 2:
                        words_dedup.add(inflect.word)

            for word in words_dedup:
                if word == entry.word:
                    ext_dictionary.append(entry)
                    continue

                ext_dictionary.append(DictEntry(word=word, flags=entry.flags, parent=entry))

        return list(set(ext_dictionary))
