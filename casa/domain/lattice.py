#!/usr/bin/env python3
"""Lattice + grid value objects."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Lattice:
    lattice_id: str
    width: int = 32
    height: int = 32
    cells: list[list[str]] = field(default_factory=list)
    z_level: int = 0
    concept_prefix: str = ""
    subsystem: str = ""

    @classmethod
    def from_dict(cls, lattice_id: str, raw: dict) -> Lattice:
        w = int(raw.get("width") or 32)
        h = int(raw.get("height") or 32)
        cells = raw.get("cells")
        if not isinstance(cells, list) or len(cells) != w * h:
            cells = [[] for _ in range(w * h)]
        return cls(
            lattice_id=lattice_id,
            width=w,
            height=h,
            cells=cells,
            z_level=int(raw.get("z_level") or raw.get("z_ctrl") or 0),
            concept_prefix=str(raw.get("concept_prefix") or ""),
            subsystem=str(raw.get("subsystem") or ""),
        )

    def to_dict(self) -> dict:
        out: dict = {
            "width": self.width,
            "height": self.height,
            "cells": self.cells,
        }
        if self.z_level:
            key = "z_ctrl" if self.subsystem == "control" else "z_level"
            out[key] = self.z_level
        if self.concept_prefix:
            out["concept_prefix"] = self.concept_prefix
        if self.subsystem:
            out["subsystem"] = self.subsystem
        return out
