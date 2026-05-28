#!/usr/bin/env python3
"""
codec_grid_v2: semantic placement for graph edges near their endpoints.

Differences vs v1:
- Adds node tokens: "N:<node_id>" for graph nodes (or inferred from edges).
- Places edge tokens "E:<src>|<rel>|<dst>" in a cluster near the midpoint of src/dst node anchors.

Why:
- v0/v1 treat each token independently, so an NCA can't infer an edge from local context.
- v2 creates locality: nodes and their incident edges co-locate.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from codec_grid_v0 import Grid, _read_json, _stable_u64, decode_grid, score_recovery  # type: ignore


def _anchor_for(key: str, width: int, height: int) -> tuple[int, int]:
    base = _stable_u64(key)
    return int(base % width), int((base // width) % height)


def _pick_cells_clustered(
    *,
    anchor: tuple[int, int],
    seed_u64: int,
    width: int,
    height: int,
    copies: int,
    radius: int,
    max_tries: int = 5000,
) -> list[tuple[int, int]]:
    ax, ay = anchor
    rng = random.Random(seed_u64 ^ 0x9E3779B97F4A7C15)
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
        dx = rng.randint(-radius, radius)
        dy = rng.randint(-radius, radius)
        if abs(dx) + abs(dy) > radius and rng.random() < 0.6:
            continue
        add(ax + dx, ay + dy)

    return out[:copies]


def encode_bundle_to_grid(
    bundle: dict,
    *,
    width: int = 64,
    height: int = 64,
    copies: int = 7,
    node_radius: int = 6,
    edge_radius: int = 4,
) -> dict:
    claims = bundle.get("claims", [])
    graph = bundle.get("graph") or {}
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []

    concept_ids = sorted({c.get("concept_id") for c in claims if c.get("concept_id")})

    # Node ids: prefer explicit nodes; otherwise infer from edges.
    node_ids: set[str] = set()
    for n in nodes:
        nid = n.get("id") if isinstance(n, dict) else None
        if nid:
            node_ids.add(str(nid))
    if not node_ids:
        for e in edges:
            src = e.get("src")
            dst = e.get("dst")
            if src:
                node_ids.add(str(src))
            if dst:
                node_ids.add(str(dst))
    node_ids_sorted = sorted(node_ids)

    # Precompute node anchors for locality.
    node_anchor: dict[str, tuple[int, int]] = {}
    for nid in node_ids_sorted:
        node_anchor[nid] = _anchor_for(f"N:{nid}", width, height)

    edge_tokens: list[str] = []
    edge_mid_anchor: dict[str, tuple[int, int]] = {}
    for e in edges:
        src = e.get("src")
        rel = e.get("relation")
        dst = e.get("dst")
        if not (src and rel and dst):
            continue
        src = str(src)
        dst = str(dst)
        t = f"E:{src}|{rel}|{dst}"
        edge_tokens.append(t)

        ax0, ay0 = node_anchor.get(src, _anchor_for(f"N:{src}", width, height))
        ax1, ay1 = node_anchor.get(dst, _anchor_for(f"N:{dst}", width, height))
        # Midpoint in toroidal space is tricky; for v2 we just average in grid coords.
        mx = (ax0 + ax1) // 2
        my = (ay0 + ay1) // 2
        edge_mid_anchor[t] = (mx, my)

    tokens = (
        [f"C:{cid}" for cid in concept_ids]
        + [f"N:{nid}" for nid in node_ids_sorted]
        + sorted(edge_tokens)
    )

    grid = Grid.empty(width, height)

    # Place concepts (independent clusters).
    for cid in concept_ids:
        t = f"C:{cid}"
        base = _stable_u64(t)
        anchor = _anchor_for(t, width, height)
        for x, y in _pick_cells_clustered(anchor=anchor, seed_u64=base, width=width, height=height, copies=copies, radius=node_radius):
            grid = grid.with_token(x, y, t)

    # Place nodes (independent clusters).
    for nid in node_ids_sorted:
        t = f"N:{nid}"
        base = _stable_u64(t)
        anchor = node_anchor[nid]
        for x, y in _pick_cells_clustered(anchor=anchor, seed_u64=base, width=width, height=height, copies=copies, radius=node_radius):
            grid = grid.with_token(x, y, t)

    # Place edges near their endpoints midpoint.
    for t in sorted(edge_tokens):
        base = _stable_u64(t)
        anchor = edge_mid_anchor[t]
        for x, y in _pick_cells_clustered(anchor=anchor, seed_u64=base, width=width, height=height, copies=copies, radius=edge_radius):
            grid = grid.with_token(x, y, t)

    return {
        "schema_version": 1,
        "codec": "codec_grid_v2",
        "width": width,
        "height": height,
        "copies": copies,
        "node_radius": node_radius,
        "edge_radius": edge_radius,
        "tokens_count": len(tokens),
        "cells": grid.cells,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Encode/decode ontology bundle into a semantic token grid (v2)")
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--out-grid", type=Path, required=True)
    p.add_argument("--width", type=int, default=64)
    p.add_argument("--height", type=int, default=64)
    p.add_argument("--copies", type=int, default=7)
    p.add_argument("--node-radius", type=int, default=6)
    p.add_argument("--edge-radius", type=int, default=4)
    p.add_argument("--min-votes", type=int, default=3)
    args = p.parse_args()

    bundle = _read_json(args.bundle)
    grid = encode_bundle_to_grid(
        bundle,
        width=args.width,
        height=args.height,
        copies=args.copies,
        node_radius=args.node_radius,
        edge_radius=args.edge_radius,
    )

    args.out_grid.parent.mkdir(parents=True, exist_ok=True)
    args.out_grid.write_text(json.dumps(grid, ensure_ascii=False, indent=2), encoding="utf-8")

    decoded = decode_grid(grid, min_votes=args.min_votes)
    score = score_recovery(bundle, decoded)
    print(json.dumps({"decoded": decoded, "score": score}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

