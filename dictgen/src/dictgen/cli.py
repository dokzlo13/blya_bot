"""CLI for dictionary generation and packing."""

import argparse
from pathlib import Path
from typing import Literal

import structlog

from blya_bot.dictionary.codec import pack
from blya_bot.dictionary.entry import DictEntry

from .dsl_dict import DslFileDict
from .morph_modifier import PyMorphyRuDictModifier

logger = structlog.getLogger(__name__)


def generate_dictionary(path: Path, *, morphing: bool = True) -> list[DictEntry]:
    """Load and optionally morph dictionary from DSL file."""
    loader = DslFileDict(equal_chars=[("е", "ё"), ("и", "й")])
    logger.info("Dict loader created", engine="DslFileDict")

    logger.info("Loading dictionary file...", path=str(path))
    dictionary = loader.load(path)
    logger.info("Dict loaded", total_loaded=len(dictionary))

    if morphing:
        logger.info("Morphing word forms...")
        dictionary = PyMorphyRuDictModifier().modify_dict(dictionary)
        logger.info("Dict morphed", total_morphed=len(dictionary))
    else:
        logger.info("Morphing disabled, skipping...")

    return dictionary


def save_dictionary(
    dictionary: list[DictEntry],
    path: Path,
    compression: Literal["zstd", "none"],
) -> None:
    """Pack and save dictionary to file."""
    packed = pack(dictionary, compression=compression)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(packed)
    logger.info("Packed dictionary written", path=str(path), bytes=len(packed))


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Generate and pack dictionary")
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        type=Path,
        help="Path to DSL dictionary text file",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        type=Path,
        help="Output packed file path",
    )
    parser.add_argument(
        "-c",
        "--compression",
        default="zstd",
        choices=["zstd", "none"],
        help="Compression type (default: zstd)",
    )
    parser.add_argument(
        "--morphing",
        "--no-morphing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable/disable morphological expansion (default: enabled)",
    )
    args = parser.parse_args()

    dictionary = generate_dictionary(args.input, morphing=args.morphing)
    save_dictionary(dictionary, args.output, args.compression)


if __name__ == "__main__":
    main()

