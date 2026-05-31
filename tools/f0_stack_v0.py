#!/usr/bin/env python3
"""F0 math lattice stack — encode/decode M: tokens on field."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from codec_grid_v0 import Grid  # type: ignore
from sss_stack_v0 import _place_token  # type: ignore


def load_f0_stack(path: Path | None = None) -> dict:
    p = path or Path("design/f0-math-lattice-stack.v0.json")
    return json.loads(p.read_text(encoding="utf-8"))


def lattice_meta_f0(stack: dict, lattice_id: str) -> dict:
    for lat in stack.get("lattices") or []:
        if lat.get("id") == lattice_id:
            return lat
    raise KeyError(lattice_id)


def encode_f0_lattice(
    bundle: dict,
    *,
    lattice_id: str = "schema-math",
    stack: dict | None = None,
    width: int = 32,
    height: int = 32,
    copies: int = 5,
) -> dict[str, Any]:
    """Place M: / C: / E: tokens for math bundle on one F lattice."""
    stack = stack or load_f0_stack()
    meta = lattice_meta_f0(stack, lattice_id)
    size = meta.get("size") or {}
    w = int(size.get("width") or width)
    h = int(size.get("height") or height)
    grid = Grid.empty(w, h)

    for item in bundle.get("math_tokens") or []:
        tok = str(item.get("token") or "")
        if tok:
            grid = _place_token(grid, tok, tok, copies=int(item.get("copies") or copies))

    for c in bundle.get("claims") or []:
        cid = str(c.get("concept_id") or "")
        if cid.startswith("math."):
            grid = _place_token(grid, f"C:{cid}", f"C:{cid}", copies=copies)

    for e in (bundle.get("graph") or {}).get("edges") or []:
        src, rel, dst = e.get("src"), e.get("relation"), e.get("dst")
        if not (src and rel and dst):
            continue
        tok = f"E:{src}|{rel}|{dst}"
        grid = _place_token(grid, tok, tok, copies=max(2, copies // 2), radius=4)

    return {
        "f_level": int(meta.get("f_level") or 0),
        "width": w,
        "height": h,
        "cells": grid.cells,
        "subsystem_id": "first_signal_math",
        "token_prefix": meta.get("token_prefix") or ["M:"],
    }


def decode_f0_lattice(lattice: dict, *, min_votes: int = 1) -> dict[str, Any]:
    vote: dict[str, int] = {}
    for cell in lattice.get("cells") or []:
        for t in cell:
            vote[t] = vote.get(t, 0) + 1

    concepts: list[dict[str, Any]] = []
    math_tokens: list[dict[str, Any]] = []
    for t, v in vote.items():
        if v < min_votes:
            continue
        if t.startswith("C:"):
            concepts.append({"concept_id": t[2:], "votes": v})
        elif t.startswith("M:"):
            math_tokens.append({"token": t, "votes": v})

    concepts.sort(key=lambda c: (-int(c["votes"]), c["concept_id"]))
    math_tokens.sort(key=lambda m: (-int(m["votes"]), m["token"]))
    edges = sorted(t[2:] for t, v in vote.items() if t.startswith("E:") and v >= min_votes)

    return {
        "min_votes": min_votes,
        "concept_ids": [c["concept_id"] for c in concepts],
        "concepts": concepts,
        "math_tokens": [m["token"] for m in math_tokens],
        "math_token_votes": math_tokens,
        "edges": edges,
        "seen_tokens": len(vote),
    }


def f0_digest(decoded: dict, *, prefix: str = "math.") -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for c in decoded.get("concepts") or []:
        cid = str(c.get("concept_id") or "")
        if cid.startswith(prefix):
            out.append((cid, int(c.get("votes") or 0)))
    out.sort(key=lambda x: (-x[1], x[0]))
    return out


def glyph_to_concept(bundle: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for g in bundle.get("math_glyphs") or []:
        glyph = str(g.get("glyph") or "")
        cid = str(g.get("concept_id") or "")
        if glyph and cid:
            out[glyph] = cid
    return out


def _score_glyphs(cue: str, gmap: dict[str, str]) -> dict[str, int]:
    """Longest-match glyph scoring (|| → math.two, not 2× math.one)."""
    scores: dict[str, int] = {}
    rest = cue
    glyphs = sorted(gmap.keys(), key=len, reverse=True)
    changed = True
    while changed:
        changed = False
        for glyph in glyphs:
            if glyph in rest:
                cid = gmap[glyph]
                scores[cid] = scores.get(cid, 0) + 4
                rest = rest.replace(glyph, " ", 1)
                changed = True
                break
    return scores


def rank_cue_on_f0(bundle: dict, decoded: dict, cue: str) -> list[tuple[str, int]]:
    """Rank math.* concepts activated by cue (glyphs, keywords) — field-only."""
    cue = cue.strip()
    scores: dict[str, int] = {}
    gmap = glyph_to_concept(bundle)
    cl = cue.lower()

    if "+" in cue:
        scores["math.add"] = scores.get("math.add", 0) + 10

    for cid, words in (bundle.get("math_keywords") or {}).items():
        for w in words:
            ws = str(w).lower()
            if ws in cl or (len(ws) == 1 and ws in cue):
                scores[str(cid)] = scores.get(str(cid), 0) + 3

    if "+" not in cue and "|" in cue:
        pipe_part = "".join(ch if ch in "|+= " else " " for ch in cue)
        for cid, pts in _score_glyphs(pipe_part, gmap).items():
            scores[cid] = scores.get(cid, 0) + pts

    base = {cid: v for cid, v in f0_digest(decoded)}
    for cid, v in base.items():
        scores[cid] = scores.get(cid, 0) + min(v, 5)

    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    return ranked
