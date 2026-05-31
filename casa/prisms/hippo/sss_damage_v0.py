#!/usr/bin/env python3
"""Structured damage on SSS memory lattices (patch holes)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import copy
from typing import Any

from layout_apply import Rect, damage_region_patches  # type: ignore


def damage_lattice(
    lattice: dict,
    *,
    patch_w: int = 8,
    patch_h: int = 8,
    count: int = 4,
    seed: int = 1,
) -> dict[str, Any]:
    w = int(lattice["width"])
    h = int(lattice["height"])
    rect = Rect(x0=0, y0=0, x1=w - 1, y1=h - 1)
    damaged = damage_region_patches(
        {"width": w, "height": h, "cells": [list(x) for x in lattice["cells"]]},
        rect,
        patch_w=patch_w,
        patch_h=patch_h,
        count=count,
        seed=seed,
    )
    out = copy.deepcopy(lattice)
    out["cells"] = damaged["cells"]
    out["damage"] = {**damaged.get("damage", {}), "lattice": True}
    return out


def damage_memory_lattices(
    lattices: dict[str, dict],
    *,
    targets: list[str] | None = None,
    patch_w: int = 8,
    patch_h: int = 8,
    count: int = 4,
    seed: int = 1,
) -> dict[str, Any]:
    """Damage selected lattices in prism_memory. Returns report."""
    lids = targets or list(lattices.keys())
    report: dict[str, Any] = {"lattices": {}, "seed": seed}
    for i, lid in enumerate(lids):
        if lid not in lattices:
            continue
        lat = damage_lattice(
            lattices[lid],
            patch_w=patch_w,
            patch_h=patch_h,
            count=count,
            seed=seed + i * 17,
        )
        lattices[lid] = lat
        report["lattices"][lid] = lat.get("damage")
    return report
