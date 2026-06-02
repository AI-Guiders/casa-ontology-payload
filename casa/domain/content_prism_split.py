#!/usr/bin/env python3
"""Move content lattices from prism_memory → domain prisms (ADR-0021 MP-5)."""

from __future__ import annotations

import re
from typing import Any

from casa.domain.prism_ids import PRISM_LANG_RU, PRISM_MATH, PRISM_MEMORY, PRISM_VISUAL
from casa.domain.visual_tract import is_visual_lattice_id
from casa.domain.prism_wire import prism_block, prism_memory, prisms
from casa.prisms.shared.lattice_names_v1 import (
    CARDINAL_MATH,
    COMPOSE_MATH,
    LEXICON_V1_RE,
    SCHEMA_MATH,
    is_lexicon_lattice,
)

# Legacy ids still on shipped stores (pre kebab migrate).
_LEGACY_LANG_RU_EXACT = frozenset(
    {
        "L0_grapheme_cyrl",
        "L1_syllable",
        "L2_word",
        "L0_punct_cyrl",
        "L0_layout_jcuken_ru",
        "L0_vk_physical",
        "words-ru",
    }
)
_LEGACY_MATH_EXACT = frozenset(
    {
        "F0_schema",
        "F1_compose",
        "F2_quantity",
        "quantity-math",
    }
)
_RE_L2_WORD_SHARD = re.compile(r"^L2_word_\d{2}$")
_RE_L3_PHRASE_SHARD = re.compile(r"^L3_phrase(_\d{2})?$")
_RE_L2_EN_SHARD = re.compile(r"^L2_en_word_\d{2}$")

_MATH_LATTICES = frozenset({SCHEMA_MATH, COMPOSE_MATH, CARDINAL_MATH})

_LANG_RU_PREFIXES = (
    "alphabet-ru",
    "alphabet-uk",
    "alphabet-be",
    "syllables-ru",
    "syllables-uk",
    "lexicon-ru",
    "phrases",
    "keys-physical",
    "layout-ru",
    "punct-ru",
)


def lattice_content_prism_target(lattice_id: str) -> str | None:
    """Target content prism for lattice_id, or None to keep in prism_memory."""
    lid = str(lattice_id)
    if is_visual_lattice_id(lid):
        return PRISM_VISUAL
    if lid in _MATH_LATTICES or lid in _LEGACY_MATH_EXACT:
        return PRISM_MATH
    if lid.startswith(("schema-", "compose-", "cardinal-")):
        return PRISM_MATH
    if lid in _LEGACY_LANG_RU_EXACT or _RE_L2_WORD_SHARD.fullmatch(lid) or _RE_L3_PHRASE_SHARD.fullmatch(lid):
        return PRISM_LANG_RU
    if any(lid == p or lid.startswith(p + "-") for p in _LANG_RU_PREFIXES):
        return PRISM_LANG_RU
    if is_lexicon_lattice(lid):
        parsed = LEXICON_V1_RE.fullmatch(lid)
        if parsed:
            loc = parsed.group(1)
            if loc.startswith("ru") or loc in ("ru", "uk", "be"):
                return PRISM_LANG_RU
            return None
        if lid == "lexicon-ru":
            return PRISM_LANG_RU
    if _RE_L2_EN_SHARD.fullmatch(lid) or lid.startswith("alphabet-en") or lid.startswith("syllables-en"):
        return None
    if lid.startswith("lexicon-en") or lid in ("L0_grapheme_latn", "L0_layout_qwerty_us", "L0_punct_latn"):
        return None
    return None


def split_content_prisms(state: dict, *, move: bool = True) -> dict[str, Any]:
    """Move classified lattices out of prism_memory (and legacy sss mirror)."""
    from casa.prisms.memory.memory_prisms import ensure_prisms, import_lattice_into_prism
    from casa.prisms.memory.prism_spawn import ensure_domain_content_stubs

    ensure_prisms(state)
    ensure_domain_content_stubs(state)

    mem = prism_memory(state)
    src: dict[str, dict] = dict(mem.get("lattices") or {})
    sss_lats: dict[str, dict] = dict((state.get("sss") or {}).get("lattices") or {})
    for lid, lat in sss_lats.items():
        src.setdefault(lid, lat)

    moved: dict[str, list[str]] = {PRISM_LANG_RU: [], PRISM_MATH: [], PRISM_MEMORY: []}
    for lid, lat in list(src.items()):
        target = lattice_content_prism_target(lid)
        if target is None:
            moved[PRISM_MEMORY].append(lid)
            continue
        moved[target].append(lid)
        if not move:
            continue
        import_lattice_into_prism(state, target, lid, lat)
        src.pop(lid, None)

    if move:
        mem["lattices"] = src
        state.setdefault("sss", {})["lattices"] = dict(src)
        _sync_active_lattice_sn(state)

    return {
        "moved": {k: sorted(v) for k, v in moved.items()},
        "remaining_in_memory": sorted(src.keys()) if move else sorted(moved[PRISM_MEMORY]),
        "counts": {k: len(v) for k, v in moved.items()},
    }


def _sync_active_lattice_sn(state: dict) -> None:
    sn = state.get("sn") or {}
    act = sn.get("active_lattice") or sn.get("active_f_lattice")
    if not act:
        return
    target = lattice_content_prism_target(str(act))
    if target == PRISM_LANG_RU:
        block = prism_block(state, PRISM_LANG_RU)
        block["active_lattice"] = act
    elif target == PRISM_MATH:
        block = prism_block(state, PRISM_MATH)
        block["active_lattice"] = act
        sn["active_prism"] = PRISM_MATH
        state["sn"] = sn
    elif target and target not in (PRISM_MEMORY,):
        return
    # default content route still uses memory for en/misc
    for pid in (PRISM_LANG_RU, PRISM_MATH):
        block = prisms(state).get(pid)
        if isinstance(block, dict) and block.get("lattices") and not block.get("active_lattice"):
            block["active_lattice"] = next(iter(block["lattices"]))
