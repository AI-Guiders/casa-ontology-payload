#!/usr/bin/env python3
"""SSS lattice ↔ NCA token grid (L2_word first)."""

from __future__ import annotations

from typing import Any

from codec_grid_v0 import decode_grid  # type: ignore


def tokens_from_lattice(lattice: dict) -> list[str]:
    seen: set[str] = set()
    for cell in lattice.get("cells") or []:
        for t in cell:
            if t:
                seen.add(str(t))
    return sorted(seen)


def lattice_as_grid(lattice: dict) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "width": int(lattice["width"]),
        "height": int(lattice["height"]),
        "cells": [list(x) for x in lattice.get("cells") or []],
    }


def grid_to_lattice_cells(grid: dict, *, token_filter: set[str] | None = None) -> list[list[str]]:
    w, h = int(grid["width"]), int(grid["height"])
    cells = grid.get("cells") or []
    out: list[list[str]] = []
    for idx in range(w * h):
        row = []
        for t in cells[idx] if idx < len(cells) else []:
            ts = str(t)
            if token_filter is not None and ts not in token_filter:
                continue
            row.append(ts)
        out.append(row)
    return out


def decode_lattice_tokens(lattice: dict, *, min_votes: int = 2) -> dict[str, Any]:
    return decode_grid(lattice_as_grid(lattice), min_votes=min_votes)


def word_tokens_from_lattice(lattice: dict) -> list[str]:
    return [t for t in tokens_from_lattice(lattice) if t.startswith("W:")]
