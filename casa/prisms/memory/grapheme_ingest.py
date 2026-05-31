#!/usr/bin/env python3
"""Derive and imprint L0 graphemes (latn/cyrl namespaces) — no tags in ingest."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.prisms.shared.prism_state import normalize_prisms, prism_memory, prism_hippo, prism_control, PRISM_MEMORY, PRISM_HIPPO, PRISM_CONTROL, set_active_prism

from typing import Any, Iterable, Literal

from casa.prisms.shared.codec_grid import Grid
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.memory.lexicon_shard import L2_CONCEPT_PREFIX, l2_word_lattice_ids
from casa.prisms.shared.lattice_names_v1 import ALPHABET_EN, ALPHABET_RU, is_alphabet_lattice
from casa.prisms.memory.stack import _place_token, decode_lattice, lattice_meta, load_stack
from casa.prisms.memory.vocab import norm_word

Script = Literal["latn", "cyrl"]
GRAPHEME_LATN_PREFIX = "grapheme.latn."
GRAPHEME_CYRL_PREFIX = "grapheme.cyrl."
L0_CYRL_ID = ALPHABET_RU
L0_LATN_ID = ALPHABET_EN
L0_GRAPHEME_IDS = (L0_CYRL_ID, L0_LATN_ID)
L0_ID_LEGACY = "L0_grapheme"  # strip/migrate scripts only


def l0_lattice_id(script: Script) -> str:
    return L0_LATN_ID if script == "latn" else L0_CYRL_ID


def is_grapheme_lattice(lattice_id: str) -> bool:
    return is_alphabet_lattice(str(lattice_id))


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
    state = ensure_prisms(state)
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


def ensure_l0_lattice(state: dict, script: Script) -> dict[str, Any]:
    state = ensure_prisms(state)
    lid = l0_lattice_id(script)
    lattices = memory_lattices(state)
    if lid in lattices:
        return lattices[lid]
    stack = load_stack()
    meta = lattice_meta(stack, lid)
    size = meta.get("size") or {}
    w = int(size.get("width") or 32)
    h = int(size.get("height") or 32)
    lat = {
        "z_level": int(meta.get("z_level") or 0),
        "width": w,
        "height": h,
        "cells": [[] for _ in range(w * h)],
        "concept_prefix": str(meta.get("concept_prefix") or (GRAPHEME_CYRL_PREFIX if script == "cyrl" else GRAPHEME_LATN_PREFIX)),
        "script": script,
    }
    lattices[lid] = lat
    prism_memory(state)["lattices"] = lattices
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
    lid = l0_lattice_id(script)
    lat = ensure_l0_lattice(state, script)
    g = Grid(width=int(lat["width"]), height=int(lat["height"]), cells=lat["cells"])
    tok = f"C:{cid}"
    g = _place_token(g, tok, tok, copies=copies, radius=5)
    glyph = ch.lower() if script == "latn" else ch
    g = _place_token(g, f"G:{glyph}", f"G:{glyph}", copies=max(2, copies - 1), radius=4)
    lat["cells"] = g.cells
    lattices = memory_lattices(state)
    lattices[lid] = lat
    prism_memory(state)["lattices"] = lattices
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
    lat = memory_lattices(state).get(l0_lattice_id(script)) or {}
    dec = decode_lattice(lat, min_votes=1)
    prefix = GRAPHEME_LATN_PREFIX if script == "latn" else GRAPHEME_CYRL_PREFIX
    on_field = sum(1 for c in dec.get("concepts") or [] if str(c.get("concept_id") or "").startswith(prefix))
    return {
        "script": script,
        "lattice_id": l0_lattice_id(script),
        "graphemes_requested": len(chars),
        "graphemes_on_field": on_field,
        "sample": placed[:8],
        "field_version": state["field_version"],
    }


def _route_legacy_l0_token(tok: str) -> Script | None:
    s = str(tok)
    if s.startswith("C:grapheme.cyrl.") or (s.startswith("E:") and GRAPHEME_CYRL_PREFIX in s):
        return "cyrl"
    if s.startswith("C:grapheme.latn.") or (s.startswith("E:") and GRAPHEME_LATN_PREFIX in s):
        return "latn"
    if s.startswith("C:grapheme."):
        tail = s[len("C:grapheme.") :]
        if tail:
            ch = tail.split(".", 1)[0]
            if ch and _is_cyrillic(ch[0]):
                return "cyrl"
            if ch and _is_latn_letter(ch[0].lower()):
                return "latn"
    if s.startswith("G:"):
        g = s[2:]
        if g and _is_latn_letter(g[0].lower()):
            return "latn"
        if g and _is_cyrillic(g[0]):
            return "cyrl"
    if s.startswith("E:") and "grapheme." in s:
        if GRAPHEME_CYRL_PREFIX in s or any(_is_cyrillic(c) for c in s if len(c) == 1):
            return "cyrl"
        if GRAPHEME_LATN_PREFIX in s:
            return "latn"
    return None


def reset_l0_script_lattice(state: dict, script: Script) -> dict[str, Any]:
    """Clear one script L0 lattice (empty cells, keep dimensions)."""
    state = ensure_prisms(state)
    lat = ensure_l0_lattice(state, script)
    w, h = int(lat.get("width") or 32), int(lat.get("height") or 32)
    lat["cells"] = [[] for _ in range(w * h)]
    lattices = memory_lattices(state)
    lattices[l0_lattice_id(script)] = lat
    prism_memory(state)["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices
    return lat


def strip_legacy_l0_monolith(state: dict, *, reimprint_alphabet: bool = True) -> dict[str, Any]:
    """Drop L0_grapheme monolith; reset cyrl/latn; optional immutable alphabet imprint."""
    from casa.prisms.memory.alphabet_core import imprint_alphabet_on_l0

    state = ensure_prisms(state)
    lattices = memory_lattices(state)
    leg = lattices.pop(L0_ID_LEGACY, None)
    report: dict[str, Any] = {"removed_legacy": leg is not None}
    for script in ("cyrl", "latn"):
        reset_l0_script_lattice(state, script)  # type: ignore[arg-type]
    if reimprint_alphabet:
        report["alphabet"] = imprint_alphabet_on_l0(state)
    state["field_version"] = int(state.get("field_version") or 0) + 1
    report["l0_lattices"] = sorted(k for k in memory_lattices(state) if k.startswith("L0_grapheme"))
    return report


def migrate_legacy_l0_grapheme(state: dict, *, default_script: Script = "cyrl") -> dict[str, Any]:
    """Split monolith L0_grapheme → L0_grapheme_cyrl + L0_grapheme_latn (idempotent)."""
    state = ensure_prisms(state)
    lattices = memory_lattices(state)
    leg = lattices.pop(L0_ID_LEGACY, None)
    if not leg:
        return {"migrated": False}
    cyrl = ensure_l0_lattice(state, "cyrl")
    latn = ensure_l0_lattice(state, "latn")
    w = max(int(leg.get("width") or 32), int(cyrl["width"]), int(latn["width"]))
    h = max(int(leg.get("height") or 32), int(cyrl["height"]), int(latn["height"]))
    n = w * h
    leg_cells = leg.get("cells") or []

    def _grow(lat: dict) -> list[list]:
        lat["width"], lat["height"] = w, h
        cells = lat.get("cells") or []
        return [list(cells[i]) if i < len(cells) else [] for i in range(n)]

    cyrl_cells = _grow(cyrl)
    latn_cells = _grow(latn)
    routed = {"cyrl": 0, "latn": 0, "skipped": 0}
    for i in range(n):
        for tok in _cell(leg_cells, i):
            script = _route_legacy_l0_token(tok)
            if script == "cyrl":
                cyrl_cells[i].append(tok)
                routed["cyrl"] += 1
            elif script == "latn":
                latn_cells[i].append(tok)
                routed["latn"] += 1
            elif str(tok).startswith(("C:", "G:", "E:")):
                script = default_script
                if script == "cyrl":
                    cyrl_cells[i].append(tok)
                    routed["cyrl"] += 1
                else:
                    latn_cells[i].append(tok)
                    routed["latn"] += 1
            else:
                routed["skipped"] += 1

    cyrl["cells"] = cyrl_cells
    latn["cells"] = latn_cells
    lattices[l0_lattice_id("cyrl")] = cyrl
    lattices[l0_lattice_id("latn")] = latn
    prism_memory(state)["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return {"migrated": True, "routed_tokens": routed}


def _cell(cells: list, idx: int) -> list:
    return list(cells[idx]) if idx < len(cells) else []


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
