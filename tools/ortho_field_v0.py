#!/usr/bin/env python3
"""Process tokens on L3: imprint, query, extract inverse after surprise."""

from __future__ import annotations

from typing import Any

from codec_grid_v0 import Grid  # type: ignore
from entity_hub_ingest_v0 import _ensure_l3_lattice  # type: ignore
from ortho_process_v0 import (  # type: ignore
    PROC_CAPITALIZE,
    PROC_LOWER,
    PROC_LOWER_WORD,
    PROC_UPPER,
    capitalize_grapheme,
    lower_grapheme,
)
from sss_cylinders_v0 import ensure_cylinders, memory_lattices  # type: ignore
from sss_stack_v0 import _place_token, decode_lattice  # type: ignore

L3_ID = "L3_phrase"


def _parse_edge(raw: str) -> tuple[str, str, str] | None:
    body = raw[2:] if raw.startswith("E:") else raw
    parts = body.split("|")
    if len(parts) != 3:
        return None
    return parts[0], parts[1], parts[2]


def l3_process_edges(state: dict) -> list[tuple[str, str, str]]:
    lat = memory_lattices(ensure_cylinders(state)).get(L3_ID) or {}
    dec = decode_lattice(lat, min_votes=1)
    out: list[tuple[str, str, str]] = []
    for raw in dec.get("edges") or []:
        parsed = _parse_edge(str(raw))
        if parsed:
            out.append(parsed)
    return out


def l3_process_ids(state: dict) -> set[str]:
    lat = memory_lattices(ensure_cylinders(state)).get(L3_ID) or {}
    dec = decode_lattice(lat, min_votes=1)
    out: set[str] = set()
    for cid in dec.get("concept_ids") or []:
        s = str(cid)
        if s.startswith("proc."):
            out.add(s)
    for raw in dec.get("edges") or []:
        parsed = _parse_edge(str(raw))
        if not parsed:
            continue
        src, _, dst = parsed
        if src.startswith("proc."):
            out.add(src)
        if dst.startswith("proc."):
            out.add(dst)
    for cell in lat.get("cells") or []:
        for t in cell:
            ts = str(t)
            if ts.startswith("P:proc."):
                out.add(ts[2:])
            if ts.startswith("C:proc."):
                out.add(ts[2:])
    return out


def imprint_l3_concept(state: dict, concept_id: str, *, copies: int = 3) -> None:
    """Place C: concept on L3 (meta / bridge, not necessarily proc.*)."""
    state = ensure_cylinders(state)
    lat = _ensure_l3_lattice(state)
    g = Grid(width=int(lat["width"]), height=int(lat["height"]), cells=lat["cells"])
    g = _place_token(g, f"C:{concept_id}", f"C:{concept_id}", copies=copies, radius=4)
    lat["cells"] = g.cells
    memory_lattices(state)[L3_ID] = lat


def imprint_process(state: dict, proc_id: str, *, copies: int = 4) -> None:
    state = ensure_cylinders(state)
    lat = _ensure_l3_lattice(state)
    g = Grid(width=int(lat["width"]), height=int(lat["height"]), cells=lat["cells"])
    tok = f"P:{proc_id}"
    g = _place_token(g, tok, tok, copies=copies, radius=4)
    g = _place_token(g, f"C:{proc_id}", f"C:{proc_id}", copies=max(2, copies - 1), radius=3)
    lat["cells"] = g.cells
    memory_lattices(state)[L3_ID] = lat


def imprint_edge(state: dict, src: str, rel: str, dst: str, *, copies: int = 3) -> None:
    state = ensure_cylinders(state)
    lat = _ensure_l3_lattice(state)
    g = Grid(width=int(lat["width"]), height=int(lat["height"]), cells=lat["cells"])
    tok = f"E:{src}|{rel}|{dst}"
    g = _place_token(g, tok, tok, copies=copies, radius=4)
    lat["cells"] = g.cells
    memory_lattices(state)[L3_ID] = lat


def imprint_capitalize_bootstrap(state: dict, *, copies: int = 4) -> dict[str, Any]:
    """Initial teaching: only Capitalize + Upper fold. No Lower."""
    imprint_process(state, PROC_CAPITALIZE, copies=copies)
    imprint_process(state, PROC_UPPER, copies=copies)
    imprint_edge(state, PROC_UPPER, "fold", PROC_CAPITALIZE, copies=copies)
    state.setdefault("ortho", {})["bootstrap"] = "capitalize_only"
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return {
        "processes": sorted(l3_process_ids(state)),
        "edges": len(l3_process_edges(state)),
    }


def has_process(state: dict, proc_id: str) -> bool:
    return proc_id in l3_process_ids(state)


def has_inverse_pair(state: dict, forward: str, inverse: str) -> bool:
    for src, rel, dst in l3_process_edges(state):
        if rel == "inverse" and src == forward and dst == inverse:
            return True
    return False


def _alphabet_samples_from_l0(state: dict) -> list[str]:
    from grapheme_ingest_v0 import GRAPHEME_CYRL_PREFIX, GRAPHEME_LATN_PREFIX  # type: ignore

    lat = memory_lattices(ensure_cylinders(state)).get("L0_grapheme") or {}
    dec = decode_lattice(lat, min_votes=1)
    chars: list[str] = []
    for cid in dec.get("concept_ids") or []:
        s = str(cid)
        if s.startswith(GRAPHEME_LATN_PREFIX):
            chars.append(s[len(GRAPHEME_LATN_PREFIX) :])
        elif s.startswith(GRAPHEME_CYRL_PREFIX):
            chars.append(s[len(GRAPHEME_CYRL_PREFIX) :])
    return sorted(set(chars))


def derive_inverse_grapheme_proc(state: dict) -> str | None:
    """
    Infer proc.grapheme.lower as inverse of capitalize using L0 alphabet samples.
    Returns inverse proc_id if derivable; does not write to field.
    """
    if not has_process(state, PROC_CAPITALIZE):
        return None
    samples = _alphabet_samples_from_l0(state)
    if not samples:
        samples = list("abc") + list("абв")
    for ch in samples:
        if len(ch) != 1:
            continue
        up = capitalize_grapheme(ch)
        if up == ch and ch.isalpha():
            continue
        if lower_grapheme(up) != ch:
            return None
    return PROC_LOWER


def extract_inverse_after_surprise(
    state: dict,
    *,
    applied_proc: str,
    canonical: str,
    surface_wrong: str,
    surface_correct: str,
) -> dict[str, Any]:
    """
    After ortho surprise: mint inverse process on L3 if derivable from forward proc.
    Does not prescribe Lower in bootstrap — only runs post-critic.
    """
    state = ensure_cylinders(state)
    rep: dict[str, Any] = {
        "applied_proc": applied_proc,
        "canonical": canonical,
        "surface_wrong": surface_wrong,
        "surface_correct": surface_correct,
        "extracted": [],
    }

    if has_process(state, PROC_LOWER):
        rep["skipped"] = "lower_already_present"
        return rep

    inverse_g = derive_inverse_grapheme_proc(state)
    if not inverse_g:
        rep["skipped"] = "cannot_derive_inverse"
        return rep

    imprint_process(state, inverse_g)
    imprint_edge(state, PROC_CAPITALIZE, "inverse", inverse_g)
    rep["extracted"].append({"forward": PROC_CAPITALIZE, "inverse": inverse_g, "rel": "inverse"})

    if applied_proc == PROC_UPPER or has_process(state, PROC_UPPER):
        imprint_process(state, PROC_LOWER_WORD)
        imprint_edge(state, PROC_UPPER, "inverse", PROC_LOWER_WORD)
        imprint_edge(state, PROC_LOWER_WORD, "fold", inverse_g)
        rep["extracted"].append(
            {"forward": PROC_UPPER, "inverse": PROC_LOWER_WORD, "rel": "inverse+fold"}
        )

    state.setdefault("ortho", {})["last_extract"] = rep
    state["field_version"] = int(state.get("field_version") or 0) + 1
    rep["processes_after"] = sorted(l3_process_ids(state))
    return rep


def apply_from_field(state: dict, word: str, proc_id: str) -> str | None:
    """Apply word-level process only if imprinted on L3."""
    if not has_process(state, proc_id):
        return None
    from ortho_process_v0 import apply_word_proc  # type: ignore

    if proc_id == PROC_UPPER and not has_process(state, PROC_CAPITALIZE):
        return None
    if proc_id == PROC_LOWER_WORD and not has_process(state, PROC_LOWER):
        return None
    return apply_word_proc(word, proc_id)
