#!/usr/bin/env python3
"""
codec_grid: a tiny symbolic codec for "ontology in field".

This is NOT NCA yet. It's a deterministic encoder/decoder that maps a bundle into a
2D grid of discrete tokens with redundancy, and then recovers the bundle from a
possibly damaged grid (masked cells).

Why: define an explicit payload + recovery metric before training a CA.
"""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _stable_u64(s: str) -> int:
    h = hashlib.blake2b(s.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(h, "little", signed=False)


@dataclass(frozen=True)
class Grid:
    width: int
    height: int
    # cell -> list of token strings (multiset; order not important)
    cells: list[list[str]]

    @staticmethod
    def empty(width: int, height: int) -> "Grid":
        return Grid(width=width, height=height, cells=[[] for _ in range(width * height)])

    def index(self, x: int, y: int) -> int:
        return y * self.width + x

    def with_token(self, x: int, y: int, token: str) -> "Grid":
        i = self.index(x, y)
        new_cells = [c[:] for c in self.cells]
        new_cells[i].append(token)
        return Grid(width=self.width, height=self.height, cells=new_cells)


def _pick_cells(key: str, width: int, height: int, copies: int) -> list[tuple[int, int]]:
    n = width * height
    base = _stable_u64(key)
    out: list[tuple[int, int]] = []
    # simple LCG walk; deterministic, no repeats guaranteed but OK for v0
    x = base % n
    step = (base // n) % n
    step = step if step != 0 else 104729  # prime-ish
    for k in range(copies):
        idx = (x + k * step) % n
        out.append((idx % width, idx // width))
    return out


def encode_bundle_to_grid(bundle: dict, *, width: int = 64, height: int = 64, copies: int = 7) -> dict:
    """
    Encode:
    - each concept_id becomes a token: "C:<concept_id>"
    - each edge becomes a token: "E:<src>|<relation>|<dst>"
    Redundancy: each token is placed into `copies` grid cells.
    """
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
        for x, y in _pick_cells(t, width, height, copies):
            grid = grid.with_token(x, y, t)

    return {
        "schema_version": 1,
        "width": width,
        "height": height,
        "copies": copies,
        "tokens_count": len(tokens),
        "cells": grid.cells,
    }


def damage_mask(grid: dict, *, drop_fraction: float, seed: int = 1) -> dict:
    """Zero-out a fraction of cells (simulated damage)."""
    rng = random.Random(seed)
    cells = [list(x) for x in grid["cells"]]
    n = len(cells)
    drop = int(n * drop_fraction)
    for idx in rng.sample(range(n), drop):
        cells[idx] = []
    out = dict(grid)
    out["cells"] = cells
    out["damage"] = {"drop_fraction": drop_fraction, "seed": seed, "dropped_cells": drop}
    return out


def decode_grid(grid: dict, *, min_votes: int = 3) -> dict:
    """
    Decode by voting:
    token is present if it appears in >= min_votes cells.
    """
    vote: dict[str, int] = {}
    for cell in grid["cells"]:
        for t in cell:
            vote[t] = vote.get(t, 0) + 1
    present = sorted([t for t, v in vote.items() if v >= min_votes])
    concepts = sorted([t[2:] for t in present if t.startswith("C:")])
    edges = [t[2:] for t in present if t.startswith("E:")]
    return {
        "schema_version": 1,
        "min_votes": min_votes,
        "concept_ids": concepts,
        "edges": edges,
        "present_tokens": len(present),
        "seen_tokens": len(vote),
    }


def score_recovery(original_bundle: dict, decoded: dict) -> dict:
    claims = original_bundle.get("claims", [])
    edges = (original_bundle.get("graph") or {}).get("edges", [])
    gt_concepts = {c.get("concept_id") for c in claims if c.get("concept_id")}
    gt_edges = set()
    for e in edges:
        src = e.get("src")
        rel = e.get("relation")
        dst = e.get("dst")
        if src and rel and dst:
            gt_edges.add(f"{src}|{rel}|{dst}")

    pred_concepts = set(decoded.get("concept_ids", []))
    pred_edges = set(decoded.get("edges", []))

    def prf(gt: set[str], pred: set[str]) -> dict:
        tp = len(gt & pred)
        fp = len(pred - gt)
        fn = len(gt - pred)
        precision = tp / (tp + fp) if (tp + fp) else 1.0
        recall = tp / (tp + fn) if (tp + fn) else 1.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 1.0
        return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}

    return {"concepts": prf(gt_concepts, pred_concepts), "edges": prf(gt_edges, pred_edges)}


def main() -> None:
    p = argparse.ArgumentParser(description="Encode/decode ontology bundle into a token grid")
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--out-grid", type=Path, required=True)
    p.add_argument("--width", type=int, default=64)
    p.add_argument("--height", type=int, default=64)
    p.add_argument("--copies", type=int, default=7)
    p.add_argument("--damage", type=float, default=0.0, help="Drop fraction of cells (0..1)")
    p.add_argument("--damage-seed", type=int, default=1)
    p.add_argument("--min-votes", type=int, default=3)
    args = p.parse_args()

    bundle = _read_json(args.bundle)
    grid = encode_bundle_to_grid(bundle, width=args.width, height=args.height, copies=args.copies)
    if args.damage > 0:
        grid = damage_mask(grid, drop_fraction=args.damage, seed=args.damage_seed)

    args.out_grid.parent.mkdir(parents=True, exist_ok=True)
    args.out_grid.write_text(json.dumps(grid, ensure_ascii=False, indent=2), encoding="utf-8")

    decoded = decode_grid(grid, min_votes=args.min_votes)
    score = score_recovery(bundle, decoded)
    print(json.dumps({"decoded": decoded, "score": score}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

