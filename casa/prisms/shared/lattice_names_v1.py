#!/usr/bin/env python3
"""Canonical v1 kebab lattice ids — runtime uses these only (no legacy lookup)."""

from __future__ import annotations

from casa._paths import REPO_ROOT

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

Script = Literal["cyrl", "latn", "latin-extended"]

_MAP_PATH = REPO_ROOT / "design" / "lattice-id-map.v1.json"

# Memory / language
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

# Lexicon (memory.lexicon shards)
LEXICON_RU = "lexicon-ru"
LEXICON_EN = "lexicon-en"

LEXICON_V1_RE = re.compile(r"^lexicon-([a-z]{2,3}(?:-[a-z0-9]+)?)-(\d{2})$")
# Corpus-range shards: lexicon-ru-а-андрейкин (dictionary word_lo–word_hi slugs)
LEXICON_RANGE_RE = re.compile(
    r"^lexicon-([a-z]{2,3}(?:-[a-z0-9]+)?)-([\da-z\u0400-\u04FF]+(?:-[\da-z\u0400-\u04FF]+)*)$"
)

# Math (prism_memory)
SCHEMA_MATH = "schema-math"
COMPOSE_MATH = "compose-math"
CARDINAL_MATH = "cardinal-math"

# Episodic (prism_hippo)
EPISODIC_SURFACE = "episodic-surface"
EPISODIC_RULE = "episodic-rule"
EPISODIC_IO = "episodic-io"
EPISODIC_SCENE = "episodic-scene"

# Control (prism_control)
CONTROL_DMN = "control-dmn"
CONTROL_SALIENCE = "control-salience"
CONTROL_WORKING_MEMORY = "control-working-memory"
CONTROL_EXECUTIVE = "control-executive"
CONTROL_PREDICT = "control-predict"
CONTROL_ATTENTION = "control-attention"
CONTROL_VALUE = "control-value"

CONTROL_STACK: tuple[str, ...] = (
    CONTROL_DMN,
    CONTROL_SALIENCE,
    CONTROL_WORKING_MEMORY,
    CONTROL_EXECUTIVE,
    CONTROL_PREDICT,
    CONTROL_ATTENTION,
    CONTROL_VALUE,
)

CONTROL_NCA_TRAIN_STACK: tuple[str, ...] = (
    CONTROL_PREDICT,
    CONTROL_ATTENTION,
    CONTROL_VALUE,
)

WORDS_V1_RE = LEXICON_V1_RE  # compat alias; prefer LEXICON_V1_RE

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
    return ALPHABET_RU if script == "cyrl" else ALPHABET_EN


def lexicon_shard_id(locale: str, shard: int) -> str:
    if shard < 0 or shard > 99:
        raise ValueError(f"shard out of range 0..99: {shard}")
    loc = str(locale).strip().lower().replace("_", "-")
    if not loc or not re.fullmatch(r"[a-z]{2,3}(-[a-z0-9]+)?", loc):
        raise ValueError(f"locale slug: {locale!r}")
    return f"lexicon-{loc}-{shard:02d}"


def is_lexicon_lattice(lattice_id: str) -> bool:
    lid = str(lattice_id)
    if lid in (LEXICON_RU, LEXICON_EN):
        return True
    return LEXICON_V1_RE.fullmatch(lid) is not None or LEXICON_RANGE_RE.fullmatch(lid) is not None


def parse_lexicon_range_lattice(lattice_id: str) -> tuple[str, str] | None:
    """Return (locale, range_slug) for lexicon-ru-wordlo-wordhi ids."""
    m = LEXICON_RANGE_RE.fullmatch(str(lattice_id))
    if not m:
        return None
    return m.group(1), m.group(2)


def parse_lexicon_shard(lattice_id: str) -> tuple[str, int] | None:
    m = LEXICON_V1_RE.fullmatch(str(lattice_id))
    if not m:
        return None
    return m.group(1), int(m.group(2))


def is_alphabet_lattice(lattice_id: str) -> bool:
    return str(lattice_id).startswith("alphabet-")


def require_lattice(lattice_id: str, lattices: dict[str, Any]) -> str:
    """Return lattice_id if present; raise KeyError otherwise."""
    lid = str(lattice_id)
    if lid not in lattices:
        raise KeyError(f"Lattice {lid!r} not in store")
    return lid


def missing_control_lattices(lattices: dict[str, Any]) -> list[str]:
    present = set(lattices.keys())
    return sorted(lid for lid in CONTROL_STACK if lid not in present)


def has_control_lattice(lattices: dict[str, Any], *, probe: str = CONTROL_DMN) -> bool:
    return probe in lattices
