from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Generator, List, Optional

from .entry import DictEntry, DictEntryFlags
from .interface import IDictionaryLoader


class GroupType(Enum):
    OPTIONAL = auto()
    MANDATORY = auto()


class Node:
    pass


@dataclass
class LiteralNode(Node):
    value: str


@dataclass
class GroupNode(Node):
    group_type: GroupType
    options: List[List[Node]]  # Each option is a list of Nodes


class DslFileDict(IDictionaryLoader):
    def __init__(self, group_separator="|", equal_chars: list[tuple[str, str]] | None = None):
        self.group_separator = group_separator
        self.equal_chars = equal_chars or []

    def load(self, file_path: Path) -> List[DictEntry]:
        entries: List[DictEntry] = []
        with file_path.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue  # Skip comments and empty lines
                entries.extend(set(self.parse_line(line)))
        return entries

    def parse_line(self, line: str) -> Generator[DictEntry, None, None]:
        original_line = line  # Keep the original line for reference
        flags = DictEntryFlags()

        # Parse flags
        if "!" in line:
            flags.exclude = True
            line = line.replace("!", "")

        if "~" in line:
            flags.exact_match = False
            line = line.replace("~", "")

        if "^" in line:
            flags.morphing = False
            line = line.replace("^", "")

        # Expand the line into words
        def expand_line(line: str):
            for word in self.expand(line):
                if word == original_line:
                    yield DictEntry(word=word, flags=flags, parent=None)
                else:
                    yield DictEntry(word=word, flags=flags, parent=DictEntry(word=original_line, flags=flags))

        yield from expand_line(line)

        for chars in self.equal_chars:
            for char in chars:
                if char in line:
                    to_add = set(chars)
                    to_add.discard(char)
                    for other_char in to_add:
                        yield from expand_line(line.replace(char, other_char))

    def expand(self, s: str) -> List[str]:
        # Parse the input string into a nested structure of Nodes
        nodes = self.parse(s)
        # Generate all combinations from the parsed structure
        expansions = self.generate(nodes)
        return expansions

    def parse(self, s: str) -> List[Node]:
        index = 0
        length = len(s)

        def parse_node(index: int, terminators: Optional[set] = None) -> tuple[List[Node], int]:
            if terminators is None:
                terminators = set()
            nodes: list[Node] = []
            while index < length:
                c = s[index]
                if c in terminators:
                    break  # Return to the caller when terminator is found
                elif c == "[" or c == "{":
                    group_type = GroupType.OPTIONAL if c == "[" else GroupType.MANDATORY
                    index += 1  # Skip the opening bracket
                    options, index = parse_group(index, group_type)
                    nodes.append(GroupNode(group_type=group_type, options=options))
                else:
                    # Parse literal characters
                    start = index
                    while index < length and s[index] not in ["[", "]", "{", "}", self.group_separator]:
                        if s[index] in terminators:
                            break
                        index += 1
                    if start < index:
                        literal = s[start:index]
                        nodes.append(LiteralNode(value=literal))
                    else:
                        # Avoid infinite loop by advancing the index
                        index += 1
            return nodes, index

        def parse_group(index: int, group_type: GroupType) -> tuple[List[Node], int]:
            options: list[Node] = []
            closing_bracket = "]" if group_type == GroupType.OPTIONAL else "}"
            terminators = {self.group_separator, closing_bracket}
            while index < length:
                # Parse an option within the group
                option_nodes, index = parse_node(index, terminators)
                options.append(option_nodes)
                if index < length:
                    c = s[index]
                    if c == self.group_separator:
                        index += 1  # Skip the separator and continue parsing options
                    elif c == closing_bracket:
                        index += 1  # Close the group parsing
                        break
                    else:
                        raise ValueError(f"Unexpected character '{c}' at position {index}")
                else:
                    raise ValueError(f"Unmatched '{'[' if group_type == GroupType.OPTIONAL else '{'}' in string: {s}")
            return options, index

        nodes, index = parse_node(index)
        if index != length:
            raise ValueError(f"Unexpected character '{s[index]}' at position {index}")
        return nodes

    def generate(self, nodes: List[Node]) -> List[str]:
        from itertools import product

        if not nodes:
            return [""]

        def expand_nodes(node_list: List[Node]) -> List[str]:
            results = [""]
            for node in node_list:
                if isinstance(node, LiteralNode):
                    results = [prefix + node.value for prefix in results]
                elif isinstance(node, GroupNode):
                    group_options = []
                    for option in node.options:
                        option_expansions = expand_nodes(option)
                        group_options.append(option_expansions)
                    if node.group_type == GroupType.OPTIONAL:
                        # Include absence of the group content
                        group_options.append([""])
                    # Efficiently compute combinations using itertools.product
                    combinations = ["".join(p) for p in product(results, sum(group_options, []))]
                    results = combinations
                else:
                    raise ValueError("Unknown node type encountered during generation")
            return results

        return expand_nodes(nodes)
