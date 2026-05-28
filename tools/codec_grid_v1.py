#!/usr/bin/env python3
"""
codec_grid_v1: same bundle<->grid format as v0, but with *clustered* placement.

Why:
- v0 spreads copies of each token across the whole grid using an LCG walk.
- That makes recovery mostly a global voting problem, which is hard for a local CA/NCA
  to learn in a transferable way.
- v1 places copies for each token in a *local cluster* around a deterministic anchor.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from codec_grid_v0 import Grid, _read_json, _stable_u64, decode_grid, score_recovery  # type: ignore


def _pick_cells_clustered(
    key: str,
    width: int,
    height: int,
    copies: int,
    *,
    radius: int = 6,
    max_tries: int = 5000,
) -> list[tuple[int, int]]:
    """
    Deterministically place `copies` cells in a local neighborhood.

    - Anchor is derived from stable hash of key.
    - Remaining cells are chosen by a deterministic RNG seeded by hash.
    - Uses wrapping (toroidal) coordinates so anchors near borders behave similarly.
    """
    n = width * height
    base = _stable_u64(key)
    ax = int(base % width)
    ay = int((base // width) % height)

    rng = random.Random(base ^ 0x9E3779B97F4A7C15)
    chosen: set[int] = set()
    out: list[tuple[int, int]] = []

    def add(x: int, y: int) -> None:
        xx = x % width
        yy = y % height
        idx = yy * width + xx
        if idx in chosen:
            return
        chosen.add(idx)
        out.append((xx, yy))

    add(ax, ay)

    tries = 0
    while len(out) < copies and tries < max_tries:
        tries += 1
        # sample within a square; bias toward center by retry
        dx = rng.randint(-radius, radius)
        dy = rng.randint(-radius, radius)
        # mildly prefer closer points
        if abs(dx) + abs(dy) > radius and rng.random() < 0.6:
            continue
        add(ax + dx, ay + dy)

    # deterministic fallback if cluster gets too many collisions
    if len(out) < copies:
        step = int(((base // n) % n) or 104729)
        x = int(base % n)
        for k in range(copies * 3):
            idx = (x + k * step) % n
            xx = idx % width
            yy = idx // width
            add(xx, yy)
            if len(out) >= copies:
                break

    return out[:copies]


def encode_bundle_to_grid(
    bundle: dict,
    *,
    width: int = 64,
    height: int = 64,
    copies: int = 7,
    radius: int = 6,
) -> dict:
    claims = bundle.get("claims", [])
    edges = (bundle.get("graph") or {}).get("edges", [])

    concept_ids = sorted({c.get("concept_id") for c in claims if c.get("concept_id")})
    edge_tokens = []
    for e in edges:
        src = e.get("src")
        rel = e.get("relation")
        dst = e.get("dst")
        if not (src and rel and dst):
            continue
        edge_tokens.append(f"E:{src}|{rel}|{dst}")

    tokens = [f"C:{cid}" for cid in concept_ids] + sorted(edge_tokens)

    grid = Grid.empty(width, height)
    for t in tokens:
        for x, y in _pick_cells_clustered(t, width, height, copies, radius=radius):
            grid = grid.with_token(x, y, t)

    return {
        "schema_version": 1,
        "codec": "codec_grid_v1",
        "width": width,
        "height": height,
        "copies": copies,
        "radius": radius,
        "tokens_count": len(tokens),
        "cells": grid.cells,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Encode/decode ontology bundle into a clustered token grid")
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--out-grid", type=Path, required=True)
    p.add_argument("--width", type=int, default=64)
    p.add_argument("--height", type=int, default=64)
    p.add_argument("--copies", type=int, default=7)
    p.add_argument("--radius", type=int, default=6)
    p.add_argument("--min-votes", type=int, default=3)
    args = p.parse_args()

    bundle = _read_json(args.bundle)
    grid = encode_bundle_to_grid(bundle, width=args.width, height=args.height, copies=args.copies, radius=args.radius)

    args.out_grid.parent.mkdir(parents=True, exist_ok=True)
    args.out_grid.write_text(json.dumps(grid, ensure_ascii=False, indent=2), encoding="utf-8")

    decoded = decode_grid(grid, min_votes=args.min_votes)
    score = score_recovery(bundle, decoded)
    print(json.dumps({"decoded": decoded, "score": score}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

