from .interface import BaseDictionaryLoader
from .dsl_dictionary import DslDictLoader
from .dsl_morph_dictionary import PyMorphyRuDslDictLoader

__all__ = ["BaseDictionaryLoader", "DslDictLoader", "PyMorphyRuDslDictLoader"]
