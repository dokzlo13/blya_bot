# Usage:
#   from blya_bot.dictionary import DictEntry, DictEntryFlags, pack, unpack
#
#   blob = pack(entries)            # entries: list[DictEntry]
#   entries2 = unpack(blob)         # -> list[DictEntry]

from __future__ import annotations

from typing import Literal

import msgpack
import zstandard as zstd

from .entry import DictEntry, DictEntryFlags

# Zstd frame magic bytes (0x28B52FFD) to detect compression safely.
_ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
_FMT_VER = 1  # format version for forward-compat


# --- Bit packing for flags ---
def _flags_to_bits(f: DictEntryFlags) -> int:
    # bit0=morphing, bit1=exclude, bit2=exact_match
    return (1 if f.morphing else 0) | ((1 if f.exclude else 0) << 1) | ((1 if f.exact_match else 0) << 2)


# Prebuild the 8 possible flag objects so we can reuse them during unpack.
_FLAGS_CACHE: tuple[DictEntryFlags, ...] = tuple(
    DictEntryFlags(
        morphing=bool(i & 1),
        exclude=bool(i & 2),
        exact_match=bool(i & 4),
    )
    for i in range(8)
)


def pack(
    entries: list[DictEntry],
    *,
    compression: Literal["zstd", "none"] = "zstd",
    dedup: bool = True,
) -> bytes:
    """Serialize a list[DictEntry] into compact bytes.

    Format (msgpack of a dict):
      {
        "ver": 1,
        "v": [str, ...],                    # vocabulary (word strings)
        "n": [[wid, fb, pidx], ...],        # unique nodes; parents precede children; pidx=-1 for None
        "e": [node_index_for_each_entry]    # original top-level entries in order
      }
    Then optionally zstd-compressed (frame magic 0x28B52FFD).
    """
    word_to_id: dict[str, int] = {}
    vocab: list[str] = []

    def intern_word(w: str) -> int:
        idx = word_to_id.get(w)
        if idx is None:
            idx = len(vocab)
            vocab.append(w)
            word_to_id[w] = idx
        return idx

    nodes: list[list[int]] = []
    node_index_by_key: dict[tuple[int, int, int], int] = {}
    # Optional identity memo speeds up when the same object identity appears multiple times
    id_to_index: dict[int, int] = {}

    def ensure_node(entry: DictEntry | None) -> int:
        if entry is None:
            return -1

        # Build the path up to an already-known node (or root), avoiding recursion
        path: list[DictEntry] = []
        seen_ids = set()
        cur: DictEntry | None = entry
        while cur is not None and id(cur) not in id_to_index:
            i = id(cur)
            if i in seen_ids:
                raise ValueError("Cycle detected in parent chain")
            seen_ids.add(i)
            path.append(cur)
            cur = cur.parent

        pidx = -1 if cur is None else id_to_index[id(cur)]

        # Now create (or reuse) nodes from root->leaf along this path
        for node in reversed(path):
            wid = intern_word(node.word)
            fb = _flags_to_bits(node.flags)
            key = (wid, fb, pidx)
            idx = node_index_by_key.get(key) if dedup else None
            if idx is None:
                idx = len(nodes)
                node_index_by_key[key] = idx
                nodes.append([wid, fb, pidx])
            # memoize identity for fast reuse if we encounter the same object again
            id_to_index[id(node)] = idx
            pidx = idx
        return pidx

    entry_ids: list[int] = [ensure_node(e) for e in entries]

    data = {
        "ver": _FMT_VER,
        "v": vocab,
        "n": nodes,
        "e": entry_ids,
    }
    raw = msgpack.packb(data, use_bin_type=True)

    if compression == "zstd":
        if zstd is None:
            raise RuntimeError("zstandard not installed. `pip install zstandard`, or use compression='none'.")
        cctx = zstd.ZstdCompressor(level=6)
        return cctx.compress(raw)
    elif compression == "none":
        return raw
    else:
        raise ValueError("compression must be 'zstd' or 'none'")


def unpack(blob: bytes) -> list[DictEntry]:
    """Deserialize bytes produced by `pack()` back into list[DictEntry].

    Auto-detects Zstd via frame magic. Rebuilds in O(n) using cached flag objects.
    """
    # Detect Zstd
    if len(blob) >= 4 and blob[:4] == _ZSTD_MAGIC:
        if zstd is None:
            raise RuntimeError("This payload is zstd-compressed, but `zstandard` is not installed.")
        dctx = zstd.ZstdDecompressor()
        buf = dctx.decompress(blob)
    else:
        buf = blob

    data = msgpack.unpackb(buf, raw=False)
    if data.get("ver") != _FMT_VER:
        raise ValueError(f"Unsupported format version: {data.get('ver')}")

    vocab: list[str] = data["v"]
    nodes: list[list[int]] = data["n"]
    entry_ids: list[int] = data["e"]

    # Rebuild nodes in a single pass; parents come first
    built: list[DictEntry] = []
    append = built.append  # local bindings for speed
    for wid, fb, pidx in nodes:
        if not (0 <= fb < 8):
            raise ValueError(f"flags out of range: {fb}")
        if not (0 <= wid < len(vocab)):
            raise ValueError(f"word id out of range: {wid}")
        parent = built[pidx] if pidx >= 0 else None
        flags = _FLAGS_CACHE[fb]
        append(DictEntry(word=vocab[wid], flags=flags, parent=parent))

    return [built[i] for i in entry_ids]

