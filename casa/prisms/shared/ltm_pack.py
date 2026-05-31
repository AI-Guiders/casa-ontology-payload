#!/usr/bin/env python3
"""LTM pack v0: compact lattice binary (vocab + sparse placements)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import struct
import zlib
from pathlib import Path
from typing import Any

MAGIC = b"LTM0"
VERSION = 1
_HEADER = struct.Struct("<4sHHI I I")  # magic, ver, w, h, vocab_n, place_n


def lattice_to_placements(lattice: dict) -> tuple[int, int, list[str], list[tuple[int, int, int]]]:
    w = int(lattice["width"])
    h = int(lattice["height"])
    cells = lattice.get("cells") or []
    token_to_i: dict[str, int] = {}
    vocab: list[str] = []
    placements: list[tuple[int, int, int]] = []

    for yi in range(h):
        for xi in range(w):
            idx = yi * w + xi
            row = cells[idx] if idx < len(cells) else []
            for t in row:
                ts = str(t)
                if not ts:
                    continue
                if ts not in token_to_i:
                    token_to_i[ts] = len(vocab)
                    vocab.append(ts)
                placements.append((token_to_i[ts], xi, yi))

    return w, h, vocab, placements


def encode_lattice(lattice: dict) -> bytes:
    w, h, vocab, placements = lattice_to_placements(lattice)
    if w > 0xFFFF or h > 0xFFFF:
        raise ValueError(f"lattice too large: {w}x{h}")
    if len(vocab) > 0xFFFF:
        raise ValueError(f"vocab too large: {len(vocab)}")
    parts: list[bytes] = [
        _HEADER.pack(MAGIC, VERSION, w, h, len(vocab), len(placements)),
    ]
    for s in vocab:
        b = s.encode("utf-8")
        if len(b) > 0xFFFF:
            raise ValueError(f"token too long: {s[:40]!r}")
        parts.append(struct.pack("<H", len(b)))
        parts.append(b)
    for ti, x, y in placements:
        parts.append(struct.pack("<HBB", ti, x, y))
    return b"".join(parts)


def decode_lattice(data: bytes) -> dict[str, Any]:
    if len(data) < _HEADER.size:
        raise ValueError("truncated LTM")
    magic, ver, w, h, vocab_n, place_n = _HEADER.unpack_from(data, 0)
    if magic != MAGIC:
        raise ValueError(f"bad magic: {magic!r}")
    if ver != VERSION:
        raise ValueError(f"unsupported LTM version: {ver}")
    off = _HEADER.size
    vocab: list[str] = []
    for _ in range(vocab_n):
        if off + 2 > len(data):
            raise ValueError("truncated vocab")
        (ln,) = struct.unpack_from("<H", data, off)
        off += 2
        vocab.append(data[off : off + ln].decode("utf-8"))
        off += ln
    n = w * h
    cells: list[list[str]] = [[] for _ in range(n)]
    for _ in range(place_n):
        if off + 4 > len(data):
            raise ValueError("truncated placements")
        ti, x, y = struct.unpack_from("<HBB", data, off)
        off += 4
        if ti >= len(vocab):
            raise ValueError(f"bad token_idx {ti}")
        if x >= w or y >= h:
            raise ValueError(f"bad coord ({x},{y}) for {w}x{h}")
        cells[y * w + x].append(vocab[ti])
    return {"width": w, "height": h, "cells": cells}


def write_ltm(path: Path, lattice: dict, *, compress: bool = False) -> dict[str, Any]:
    raw = encode_lattice(lattice)
    path.parent.mkdir(parents=True, exist_ok=True)
    if compress:
        try:
            import zstandard as zstd  # type: ignore

            cdata = zstd.ZstdCompressor(level=3).compress(raw)
            out = path.with_suffix(path.suffix + ".zst")
            out.write_bytes(cdata)
            written = out
            comp = "zstd"
        except ImportError:
            cdata = zlib.compress(raw, level=6)
            out = path.with_suffix(path.suffix + ".gz")
            out.write_bytes(cdata)
            written = out
            comp = "gzip"
    else:
        path.write_bytes(raw)
        written = path
        comp = None
    w, h, vocab, placements = lattice_to_placements(lattice)
    return {
        "path": str(written),
        "compress": comp,
        "raw_bytes": len(raw),
        "file_bytes": written.stat().st_size,
        "vocab": len(vocab),
        "placements": len(placements),
        "width": w,
        "height": h,
    }


def read_ltm(path: Path) -> dict[str, Any]:
    if path.suffix == ".zst" or path.name.endswith(".ltm.zst"):
        import zstandard as zstd  # type: ignore

        data = zstd.ZstdDecompressor().decompress(path.read_bytes())
    elif path.suffix == ".gz" or path.name.endswith(".ltm.gz"):
        data = zlib.decompress(path.read_bytes())
    else:
        data = path.read_bytes()
    return decode_lattice(data)


def lattice_subdir(lattice_id: str) -> str:
    from casa.prisms.shared.store_paths_v1 import canonical_ltm_subdir

    return canonical_ltm_subdir(lattice_id).as_posix()
