#!/usr/bin/env python3
"""Lattice ids v1: alphabet/syllables per locale; script is metadata."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

Script = Literal["cyrl", "latn", "latin-extended"]

_MAP_PATH = Path(__file__).resolve().parent.parent / "design" / "lattice-id-map.v1.json"

# Per-locale alphabets (L0)
ALPHABET_RU = "alphabet-ru"
ALPHABET_UK = "alphabet-uk"
ALPHABET_BE = "alphabet-be"
ALPHABET_EN = "alphabet-en"
ALPHABET_DE = "alphabet-de"

SYLLABLES_RU = "syllables-ru"
SYLLABLES_UK = "syllables-uk"
SYLLABLES_EN = "syllables-en"

PHRASES = "phrases"
KEYS_PHYSICAL = "keys-physical"
LAYOUT_EN_US = "layout-en-us"
LAYOUT_RU_JCUKEN = "layout-ru-jcuken"

WORDS_RU_LEGACY_PREFIX = "L2_word_"
WORDS_EN_LEGACY_PREFIX = "L2_en_word_"
WORDS_V1_RE = re.compile(r"^words-([a-z]{2,3}(?:-[a-z0-9]+)?)-(\d{2})$")

# Deprecated v1.1 names (do not use for new lattices)
ALPHABET_CYRL = ALPHABET_RU
ALPHABET_LATN = ALPHABET_EN


@lru_cache(maxsize=1)
def _map_doc() -> dict:
    return json.loads(_MAP_PATH.read_text(encoding="utf-8"))


def alphabet_id(locale: str) -> str:
    """Orthographic alphabet for a language: alphabet-ru, alphabet-uk, …"""
    loc = str(locale).strip().lower().split("-", 1)[0]
    by_loc = (_map_doc().get("alphabet_by_locale") or {}).get(loc)
    if isinstance(by_loc, dict) and by_loc.get("id"):
        return str(by_loc["id"])
    return f"alphabet-{loc}"


def syllables_id(locale: str) -> str:
    loc = str(locale).strip().lower().split("-", 1)[0]
    return f"syllables-{loc}"


def script_for_locale(locale: str) -> Script:
    loc = str(locale).strip().lower().split("-", 1)[0]
    by_loc = (_map_doc().get("alphabet_by_locale") or {}).get(loc)
    if isinstance(by_loc, dict) and by_loc.get("script"):
        s = str(by_loc["script"])
        if s == "latin-extended":
            return "latin-extended"
        return "cyrl" if s == "cyrl" else "latn"
    if loc in ("ru", "uk", "be", "bg", "sr"):
        return "cyrl"
    if loc in ("de", "pl", "cs"):
        return "latin-extended"
    return "latn"


def alphabet_id_for_script(script: Script) -> str:
    """Legacy helper: cyrl→alphabet-ru, latn→alphabet-en only. Prefer alphabet_id(locale)."""
    return ALPHABET_RU if script == "cyrl" else ALPHABET_EN


def words_shard_id(locale: str, shard: int) -> str:
    if shard < 0 or shard > 99:
        raise ValueError(f"shard out of range 0..99: {shard}")
    loc = str(locale).strip().lower().replace("_", "-")
    if not loc or not re.fullmatch(r"[a-z]{2,3}(-[a-z0-9]+)?", loc):
        raise ValueError(f"locale slug: {locale!r}")
    return f"words-{loc}-{shard:02d}"


def legacy_words_shard_id(locale: str, shard: int) -> str:
    loc = str(locale).lower().split("-", 1)[0]
    if loc == "ru":
        return f"{WORDS_RU_LEGACY_PREFIX}{shard:02d}"
    if loc == "en":
        return f"{WORDS_EN_LEGACY_PREFIX}{shard:02d}"
    return words_shard_id(locale, shard)


def is_words_lattice(lattice_id: str) -> bool:
    lid = str(lattice_id)
    if lid in ("L2_word", "words-ru", "words-en"):
        return True
    if lid.startswith(WORDS_RU_LEGACY_PREFIX) or lid.startswith(WORDS_EN_LEGACY_PREFIX):
        return True
    return WORDS_V1_RE.fullmatch(lid) is not None


def is_alphabet_lattice(lattice_id: str) -> bool:
    lid = str(lattice_id)
    if lid.startswith("alphabet-"):
        return True
    return lid in ("L0_grapheme_cyrl", "L0_grapheme_latn", "L0_grapheme")


def legacy_to_v1(lattice_id: str) -> str:
    lid = str(lattice_id)
    doc = _map_doc()
    fixed = doc.get("legacy_to_v1") or {}
    if lid in fixed:
        return str(fixed[lid])
    for rule in doc.get("pattern_legacy_to_v1") or []:
        m = re.fullmatch(str(rule["match"]), lid)
        if m:
            return m.expand(str(rule["replace"]))
    return lid


def v1_to_legacy(lattice_id: str) -> str:
    lid = str(lattice_id)
    doc = _map_doc()
    fixed = doc.get("legacy_to_v1") or {}
    for legacy, v1 in fixed.items():
        if v1 == lid:
            return legacy
    m = re.fullmatch(r"words-ru-(\d{2})", lid)
    if m:
        return f"L2_word_{m.group(1)}"
    m = re.fullmatch(r"words-en-(\d{2})", lid)
    if m:
        return f"L2_en_word_{m.group(1)}"
    return lid


def resolve_lattice_id(lattice_id: str, *, prefer: Literal["v1", "legacy"] = "v1") -> str:
    lid = str(lattice_id)
    if prefer == "v1":
        return legacy_to_v1(lid)
    return v1_to_legacy(lid)


def resolve_store_lattice_id(lattice_id: str, lattices: dict[str, Any]) -> str:
    """Pick id that exists in store (v1 preferred; legacy CLI args still work)."""
    lid = str(lattice_id)
    v1 = legacy_to_v1(lid)
    if v1 in lattices:
        return v1
    if lid in lattices:
        return lid
    raise KeyError(f"Lattice {lid!r} (v1={v1!r}) not in store")


def parse_words_shard(lattice_id: str) -> tuple[str, int] | None:
    lid = str(lattice_id)
    m = WORDS_V1_RE.fullmatch(lid)
    if m:
        return m.group(1), int(m.group(2))
    if lid.startswith(WORDS_RU_LEGACY_PREFIX):
        return "ru", int(lid[len(WORDS_RU_LEGACY_PREFIX) :])
    if lid.startswith(WORDS_EN_LEGACY_PREFIX):
        return "en", int(lid[len(WORDS_EN_LEGACY_PREFIX) :])
    return None
