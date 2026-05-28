#!/usr/bin/env python3
"""
layout_apply: helpers for applying region-based CASA layout to a token grid.

Given:
- a bundle (concepts+edges) -> token grid (codec_grid_v0)
- a layout (design/layout.v0.json)

We can:
- mask tokens outside a region (e.g. DMN only)
- inject damage inside a region only

This is a scaffold for region-local training/evaluation.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


@dataclass(frozen=True)
class Rect:
    x0: int
    y0: int
    x1: int
    y1: int

    def contains(self, x: int, y: int) -> bool:
        return self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1


def _rect_from(obj: dict) -> Rect:
    return Rect(x0=int(obj["x0"]), y0=int(obj["y0"]), x1=int(obj["x1"]), y1=int(obj["y1"]))


def _get_region_rect(layout: dict, region_id: str) -> Rect:
    for r in layout.get("regions", []):
        if r.get("id") == region_id:
            return _rect_from(r["rect"])
    raise KeyError(f"region not found: {region_id}")


def mask_outside_region(grid: dict, rect: Rect) -> dict:
    """Clear tokens in cells outside rect."""
    w = int(grid["width"])
    h = int(grid["height"])
    cells = [list(x) for x in grid["cells"]]
    for y in range(h):
        for x in range(w):
            if not rect.contains(x, y):
                cells[y * w + x] = []
    out = dict(grid)
    out["cells"] = cells
    out["mask"] = {"type": "outside_region_cleared", "rect": rect.__dict__}
    return out


def damage_region(grid: dict, rect: Rect, *, drop_fraction: float, seed: int) -> dict:
    """Drop a fraction of cells inside rect only."""
    w = int(grid["width"])
    h = int(grid["height"])
    idxs = []
    for y in range(h):
        for x in range(w):
            if rect.contains(x, y):
                idxs.append(y * w + x)
    rng = random.Random(seed)
    drop = int(len(idxs) * drop_fraction)
    chosen = set(rng.sample(idxs, drop))
    cells = [list(x) for x in grid["cells"]]
    for i in chosen:
        cells[i] = []
    out = dict(grid)
    out["cells"] = cells
    out["damage"] = {"type": "region_drop", "drop_fraction": drop_fraction, "seed": seed, "dropped_cells": drop, "rect": rect.__dict__}
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Mask/damage a token grid according to layout regions")
    p.add_argument("--layout", type=Path, required=True)
    p.add_argument("--grid", type=Path, required=True)
    p.add_argument("--region", default="dmn_ontology")
    p.add_argument("--mask-outside", action="store_true", default=False)
    p.add_argument("--damage", type=float, default=0.0)
    p.add_argument("--damage-seed", type=int, default=1)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    layout = _read_json(args.layout)
    grid = _read_json(args.grid)
    rect = _get_region_rect(layout, args.region)

    out = grid
    if args.mask_outside:
        out = mask_outside_region(out, rect)
    if args.damage and args.damage > 0:
        out = damage_region(out, rect, drop_fraction=args.damage, seed=args.damage_seed)

    _write_json(args.out, out)


if __name__ == "__main__":
    main()

