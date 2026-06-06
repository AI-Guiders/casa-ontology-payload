#!/usr/bin/env python3
"""Semantic memory layer ids (replace L0…L3 / T0…T3 in prose and tooling).

Canon: design/naming-memory-layers.md, design/prisms/memory/stack.json
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from casa._paths import REPO_ROOT
from casa.prisms.shared.lattice_names_v1 import (
    LEXICON_RANGE_RE,
    LEXICON_V1_RE,
    is_alphabet_lattice,
    is_lexicon_lattice,
    parse_lexicon_range_lattice,
)

_STACK_PATH = REPO_ROOT / "design" / "prisms" / "memory" / "stack.json"

# z_level (APLF T*) → semantic layer (prose canon)
Z_TO_LAYER: dict[int, str] = {
    0: "memory.grapheme",
    1: "memory.syllable",
    2: "memory.lexicon",
    3: "memory.phrase",
}

LAYER_TO_Z: dict[str, int] = {v: k for k, v in Z_TO_LAYER.items()}

# Legacy L* labels → semantic (migrate-only / log compatibility)
LEGACY_L_TO_LAYER: dict[str, str] = {
    "L0": "memory.grapheme",
    "L1": "memory.syllable",
    "L2": "memory.lexicon",
    "L3": "memory.phrase",
    "T0": "memory.grapheme",
    "T1": "memory.syllable",
    "T2": "memory.lexicon",
    "T3": "memory.phrase",
    "B0": "memory.grapheme",
    "B1": "memory.syllable",
    "B2": "memory.lexicon",
    "B3": "memory.phrase",
}

LAYER_LABEL_RU: dict[str, str] = {
    "memory.grapheme": "графема / алфавит",
    "memory.syllable": "слог",
    "memory.lexicon": "лексикон (слова)",
    "memory.phrase": "фраза / поле (POS, entity)",
    "memory.lexicon.shard": "лексикон — shard",
    "memory.grapheme.cyrl": "алфавит (кириллица)",
    "memory.grapheme.latn": "алфавит (латиница)",
}

_PHRASES_RANGE_RE = re.compile(r"^phrases-\d{2}$")
_L3_LEGACY_RE = re.compile(r"^L3_phrase(_\d{2})?$")


@lru_cache(maxsize=1)
def _stack_doc() -> dict[str, Any]:
    if not _STACK_PATH.is_file():
        return {}
    return json.loads(_STACK_PATH.read_text(encoding="utf-8"))


def memory_layer_for_z(z_level: int | None) -> str:
    if z_level is None:
        return "memory.unknown"
    return Z_TO_LAYER.get(int(z_level), f"memory.z{int(z_level)}")


def z_level_for_memory_layer(layer: str) -> int | None:
    base = str(layer or "").strip().lower()
    if base in LAYER_TO_Z:
        return LAYER_TO_Z[base]
    for key, z in LAYER_TO_Z.items():
        if base.startswith(key + ".") or base == key:
            return z
    return None


def legacy_l_code_to_layer(code: str) -> str | None:
    """L0, T2, B3 → memory.* layer."""
    key = str(code or "").strip().upper()
    return LEGACY_L_TO_LAYER.get(key)


def memory_layer_for_lattice_id(lattice_id: str) -> str:
    """Infer semantic memory layer from lattice_id (v1 kebab or legacy L*)."""
    lid = str(lattice_id or "").strip()
    if not lid:
        return "memory.unknown"

    if is_alphabet_lattice(lid) or lid.startswith("L0_") or lid.startswith("layout-") or lid.startswith("keys-"):
        if "latn" in lid or lid.endswith("-en") or "en-us" in lid:
            return "memory.grapheme.latn"
        return "memory.grapheme.cyrl"

    if lid.startswith("syllables-") or lid == "L1_syllable":
        return "memory.syllable"

    if (
        is_lexicon_lattice(lid)
        or LEXICON_RANGE_RE.fullmatch(lid)
        or lid.startswith("L2_word")
        or lid.startswith("L2_en_word")
        or lid.startswith("words-")
    ):
        if lid in ("lexicon-ru", "lexicon-en", "L2_word", "words-ru", "words-en"):
            return "memory.lexicon.monolith"
        return "memory.lexicon.shard"

    if (
        lid in ("phrases", "L3_phrase")
        or _PHRASES_RANGE_RE.fullmatch(lid)
        or _L3_LEGACY_RE.fullmatch(lid)
        or (lid.startswith("phrases-") and lid != "phrases")
    ):
        return "memory.phrase"

    if parse_lexicon_range_lattice(lid):
        return "memory.lexicon.shard"

    # Fallback: stack.json exact match
    for row in _stack_doc().get("lattices") or []:
        if isinstance(row, dict) and str(row.get("lattice_id") or "") == lid:
            return str(row.get("semantic_id") or memory_layer_for_z(row.get("z_level")))

    return "memory.unknown"


def memory_layer_heading(layer: str, *, locale: str = "ru") -> str:
    """One-line heading for MEMORY.md / logs."""
    base = str(layer or "memory.unknown")
    ru = LAYER_LABEL_RU.get(base) or LAYER_LABEL_RU.get(base.split(".", 2)[0] + "." + base.split(".", 1)[1] if "." in base else "")
    z = z_level_for_memory_layer(base)
    t = f"T{z}" if z is not None else "?"
    if locale == "ru" and ru:
        return f"{base} ({t} · {ru})"
    return f"{base} ({t})"


def layer_sort_key(layer: str) -> tuple[int, str]:
    z = z_level_for_memory_layer(layer)
    return (z if z is not None else 99, layer)
