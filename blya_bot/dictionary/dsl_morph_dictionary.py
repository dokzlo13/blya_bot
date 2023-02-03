import warnings

import structlog

from .dsl_dictionary import DslDictLoader

logger = structlog.getLogger(__name__)


class PyMorphyRuDslDictLoader(DslDictLoader):
    def __init__(self, morph=None) -> None:
        if morph:
            self.morph = morph
        else:
            try:
                import pymorphy2
                import pymorphy2_dicts_ru

                self.morph = pymorphy2.MorphAnalyzer(path=pymorphy2_dicts_ru.get_path())

            except ImportError:
                warnings.warn("Morphological extension is not available, install 'pymorphy2' and 'pymorphy2-dicts-ru'")
                raise

    def get_all_morphs(self, word: str) -> set[str]:
        words_set: set[str] = set()
        words_set.add(word)
        for variant in self.morph.parse(word):
            for inflect in variant.lexeme:
                dict_word = self.normalize_text(inflect.word)
                if len(dict_word) > 2:
                    words_set.add(dict_word)
        return words_set

    def product_morphs(self, words: set[str]) -> set[str]:
        words_set: set[str] = set()
        for word in words:
            words_set.update(self.get_all_morphs(word))
        return words_set

    def parse_dictionary(self, rows: list[str], extend_by_morphing: bool = True) -> list[str]:
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
                temp_words = self.product_variants(word.replace("~", ""))
                if use_morph_this_word:
                    exclude_words.update(self.product_morphs(temp_words))
                else:
                    exclude_words.update(temp_words)
            else:
                temp_words = self.product_variants(word)
                if use_morph_this_word:
                    all_words.update(self.product_morphs(temp_words))
                else:
                    all_words.update(temp_words)

        done_dict = sorted(list(all_words - exclude_words))
        logger.info("Dictionary generated", raw_words=raw_words_read, final_dict=len(done_dict))
        return done_dict
