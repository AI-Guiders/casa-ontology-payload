#!/usr/bin/env python3
"""
SSS scaffold (second signal system) — place sign tokens in DMN layers.

Not "bukvar encode". See design/second-signal-system-v0.md.
Lab filename bukvar_* is temporary.
"""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import json
from pathlib import Path

from casa.prisms.shared.codec_grid_v0 import Grid, _stable_u64, decode_grid
from casa.prisms.shared.codec_grid_v2 import _pick_cells_clustered
from casa.prisms.shared.layout_apply import Rect, _get_region_rect, mask_outside_region


def layer_region_id(concept_id: str) -> str:
    cid = concept_id or ""
    if cid.startswith("grapheme."):
        return "dmn_b0_grapheme"
    if cid.startswith("syllable."):
        return "dmn_b1_syllable"
    if cid.startswith("lang.word."):
        return "dmn_b2_word"
    if cid.startswith("ru.dialog."):
        return "dmn_b3_phrase"
    return "dmn_b0_grapheme"


def _anchor_in_rect(key: str, rect: Rect, width: int, height: int) -> tuple[int, int]:
    base = _stable_u64(key)
    w = rect.x1 - rect.x0 + 1
    h = rect.y1 - rect.y0 + 1
    return rect.x0 + int(base % w), rect.y0 + int((base // max(w, 1)) % h)


def _cells_in_rect(
    key: str,
    rect: Rect,
    width: int,
    height: int,
    copies: int,
    *,
    radius: int = 4,
) -> list[tuple[int, int]]:
    ax, ay = _anchor_in_rect(key, rect, width, height)
    out: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    for x, y in _pick_cells_clustered(key, width, height, copies, radius=radius):
        if not rect.contains(x, y):
            # bias cluster toward rect center
            cx = min(max(x, rect.x0), rect.x1)
            cy = min(max(y, rect.y0), rect.y1)
            x, y = cx, cy
        if (x, y) not in seen:
            seen.add((x, y))
            out.append((x, y))
    if not out:
        out.append((ax, ay))
    return out[:copies]


def _grid_to_dict(g: Grid) -> dict:
    return {"width": g.width, "height": g.height, "cells": g.cells}


def encode_bukvar_bundle(
    bundle: dict,
    layout: dict,
    *,
    width: int = 64,
    height: int = 64,
    copies: int = 5,
) -> dict:
    """Encode concepts and compose edges into layered DMN bands."""
    claims = bundle.get("claims") or []
    edges = (bundle.get("graph") or {}).get("edges") or []
    grid = Grid.empty(width, height)

    concept_ids = sorted({str(c["concept_id"]) for c in claims if c.get("concept_id")})
    for cid in concept_ids:
        region = layer_region_id(cid)
        rect = _get_region_rect(layout, region)
        token = f"C:{cid}"
        for x, y in _cells_in_rect(token, rect, width, height, copies):
            grid = grid.with_token(x, y, token)

    for e in edges:
        src, rel, dst = e.get("src"), e.get("relation"), e.get("dst")
        if not (src and rel and dst):
            continue
        region = layer_region_id(str(dst))
        rect = _get_region_rect(layout, region)
        token = f"E:{src}|{rel}|{dst}"
        for x, y in _cells_in_rect(token, rect, width, height, max(2, copies // 2), radius=3):
            grid = grid.with_token(x, y, token)

    dmn_union = Rect(x0=0, y0=0, x1=31, y1=63)
    full = _grid_to_dict(grid)
    return mask_outside_region(full, dmn_union)


def decode_bukvar_layer(
    grid: dict,
    layout: dict,
    region_id: str,
    *,
    min_votes: int = 1,
) -> dict:
    """Decode concepts with votes, restricted to cells inside region."""
    rect = _get_region_rect(layout, region_id)
    w, h = int(grid["width"]), int(grid["height"])
    masked = Grid.empty(w, h)
    cells = grid["cells"]
    for y in range(h):
        for x in range(w):
            if rect.contains(x, y):
                i = y * w + x
                for t in cells[i]:
                    masked = masked.with_token(x, y, t)
    return decode_grid(_grid_to_dict(masked), min_votes=min_votes)


def layer_digest(decoded: dict, *, prefix: str) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for c in decoded.get("concepts") or []:
        cid = str(c.get("concept_id") or "")
        if cid.startswith(prefix):
            out.append((cid, int(c.get("votes") or 0)))
    out.sort(key=lambda x: (-x[1], x[0]))
    return out


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--layout", type=Path, default=Path("design/layout.v1.json"))
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()
    layout = json.loads(args.layout.read_text(encoding="utf-8"))
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    grid = encode_bukvar_bundle(bundle, layout)
    data = json.dumps(grid, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(data, encoding="utf-8")
    print(data)
