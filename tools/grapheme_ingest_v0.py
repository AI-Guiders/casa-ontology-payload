#!/usr/bin/env python3
"""Derive and imprint L0 graphemes (latn/cyrl namespaces) — no tags in ingest."""

from __future__ import annotations

from typing import Any, Iterable, Literal

from codec_grid_v0 import Grid  # type: ignore
from sss_cylinders_v0 import ensure_cylinders, memory_lattices  # type: ignore
from sss_l2_shard_v0 import L2_CONCEPT_PREFIX, l2_word_lattice_ids  # type: ignore
from sss_stack_v0 import _place_token, decode_lattice, lattice_meta, load_stack  # type: ignore
from sss_vocab_v0 import norm_word  # type: ignore

Script = Literal["latn", "cyrl"]
GRAPHEME_LATN_PREFIX = "grapheme.latn."
GRAPHEME_CYRL_PREFIX = "grapheme.cyrl."
L0_ID = "L0_grapheme"


def _is_cyrillic(ch: str) -> bool:
    return len(ch) == 1 and "\u0400" <= ch <= "\u04ff"


def _is_latn_letter(ch: str) -> bool:
    return len(ch) == 1 and ("a" <= ch <= "z")


def concept_id_for_grapheme(ch: str, script: Script) -> str:
    c = ch.lower() if script == "latn" else ch
    prefix = GRAPHEME_LATN_PREFIX if script == "latn" else GRAPHEME_CYRL_PREFIX
    return f"{prefix}{c}"


def derive_graphemes_from_words(words: Iterable[str], script: Script) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in words:
        w = norm_word(raw) if script == "latn" else raw.strip().lower()
        for ch in w:
            if ch in "-'":
                continue
            if script == "latn" and _is_latn_letter(ch):
                if ch not in seen:
                    seen.add(ch)
                    out.append(ch)
            elif script == "cyrl" and _is_cyrillic(ch):
                low = ch.lower()
                if low not in seen:
                    seen.add(low)
                    out.append(low)
    return sorted(out)


def derive_cyrl_graphemes_from_ru_l2(state: dict) -> list[str]:
    """Unique Cyrillic letters from RU L2 shards only."""
    state = ensure_cylinders(state)
    lattices = memory_lattices(state)
    seen: set[str] = set()
    for lid in l2_word_lattice_ids(state):
        if lid.startswith("L2_en_word_"):
            continue
        lat = lattices.get(lid) or {}
        dec = decode_lattice(lat, min_votes=1)
        for cid in dec.get("concept_ids") or []:
            s = str(cid)
            if not s.startswith(L2_CONCEPT_PREFIX):
                continue
            w = s[len(L2_CONCEPT_PREFIX) :]
            for ch in w:
                if _is_cyrillic(ch):
                    seen.add(ch.lower())
    return sorted(seen)


def ensure_l0_lattice(state: dict) -> dict[str, Any]:
    state = ensure_cylinders(state)
    lattices = memory_lattices(state)
    if L0_ID in lattices:
        return lattices[L0_ID]
    stack = load_stack()
    meta = lattice_meta(stack, L0_ID)
    size = meta.get("size") or {}
    w = int(size.get("width") or 32)
    h = int(size.get("height") or 32)
    lat = {
        "z_level": int(meta.get("z_level") or 0),
        "width": w,
        "height": h,
        "cells": [[] for _ in range(w * h)],
        "concept_prefix": str(meta.get("concept_prefix") or "grapheme."),
    }
    lattices[L0_ID] = lat
    state["cylinders"]["cyl_memory"]["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices
    return lat


def strengthen_grapheme_on_l0(
    state: dict,
    ch: str,
    script: Script,
    *,
    copies: int = 4,
) -> str:
    cid = concept_id_for_grapheme(ch, script)
    lat = ensure_l0_lattice(state)
    g = Grid(width=int(lat["width"]), height=int(lat["height"]), cells=lat["cells"])
    tok = f"C:{cid}"
    g = _place_token(g, tok, tok, copies=copies, radius=5)
    glyph = ch.lower() if script == "latn" else ch
    g = _place_token(g, f"G:{glyph}", f"G:{glyph}", copies=max(2, copies - 1), radius=4)
    lat["cells"] = g.cells
    lattices = memory_lattices(state)
    lattices[L0_ID] = lat
    state["cylinders"]["cyl_memory"]["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices
    return cid


def ingest_graphemes_batch(
    state: dict,
    chars: list[str],
    script: Script,
    *,
    copies: int = 4,
) -> dict[str, Any]:
    placed: list[str] = []
    for ch in chars:
        placed.append(strengthen_grapheme_on_l0(state, ch, script, copies=copies))
    state["field_version"] = int(state.get("field_version") or 0) + 1
    lat = memory_lattices(state).get(L0_ID) or {}
    dec = decode_lattice(lat, min_votes=1)
    prefix = GRAPHEME_LATN_PREFIX if script == "latn" else GRAPHEME_CYRL_PREFIX
    on_field = sum(1 for c in dec.get("concepts") or [] if str(c.get("concept_id") or "").startswith(prefix))
    return {
        "script": script,
        "graphemes_requested": len(chars),
        "graphemes_on_field": on_field,
        "sample": placed[:8],
        "field_version": state["field_version"],
    }


def merge_l0_lattices(base_lat: dict, overlay_lat: dict) -> dict:
    """Concatenate cell tokens; overlay wins on dimension mismatch only if larger."""
    bw, bh = int(base_lat.get("width") or 32), int(base_lat.get("height") or 32)
    ow, oh = int(overlay_lat.get("width") or 32), int(overlay_lat.get("height") or 32)
    w, h = max(bw, ow), max(bh, oh)
    n = w * h
    base_cells = base_lat.get("cells") or []
    over_cells = overlay_lat.get("cells") or []

    def _cell(cells: list, idx: int) -> list:
        return list(cells[idx]) if idx < len(cells) else []

    merged_cells: list[list] = []
    for i in range(n):
        merged_cells.append(_cell(base_cells, i) + _cell(over_cells, i))

    out = {**base_lat, "width": w, "height": h, "cells": merged_cells}
    if overlay_lat.get("locale"):
        out["locale"] = overlay_lat["locale"]
    return out


def bootstrap_linked_graphemes(
    state: dict,
    *,
    en_words: list[str],
    include_ru_l2_cyrl: bool = True,
    copies: int = 4,
) -> dict[str, Any]:
    """Derive latn L0 from EN words + cyrl L0 from RU L2 (no tags)."""
    latn = derive_graphemes_from_words(en_words, "latn")
    latn_rep = ingest_graphemes_batch(state, latn, "latn", copies=copies)
    cyrl: list[str] = []
    cyrl_rep: dict[str, Any] | None = None
    if include_ru_l2_cyrl:
        cyrl = derive_cyrl_graphemes_from_ru_l2(state)
        cyrl_rep = ingest_graphemes_batch(state, cyrl, "cyrl", copies=copies)
    return {
        "latn": latn_rep,
        "cyrl": cyrl_rep,
        "latn_count": len(latn),
        "cyrl_count": len(cyrl),
    }
