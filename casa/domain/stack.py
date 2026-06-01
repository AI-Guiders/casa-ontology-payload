#!/usr/bin/env python3
"""Stack SSOT from design/prisms/*/stack.json (read-only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from casa.prisms.shared.config_io import load_config


@dataclass(frozen=True)
class LatticeSpec:
    lattice_id: str
    legacy_id: str
    z_level: int
    concept_prefix: str
    width: int
    height: int
    status: str = ""

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> LatticeSpec:
        lid = str(row.get("legacy_id") or row.get("lattice_id") or row.get("id") or "")
        size = row.get("size") or {}
        z = int(row.get("z_level") or row.get("z_ctrl") or 0)
        return cls(
            lattice_id=lid,
            legacy_id=str(row.get("legacy_id") or lid),
            z_level=z,
            concept_prefix=str(row.get("concept_prefix") or ""),
            width=int(size.get("width") or 32),
            height=int(size.get("height") or 32),
            status=str(row.get("status") or ""),
        )


@dataclass(frozen=True)
class StackSpec:
    prism_id: str
    kind: str
    stack_path: str
    lattices: tuple[LatticeSpec, ...] = ()
    semantic_namespace: str = ""

    @classmethod
    def from_dict(cls, path: str | Path, raw: dict[str, Any]) -> StackSpec:
        rows = [LatticeSpec.from_row(r) for r in raw.get("lattices") or [] if isinstance(r, dict)]
        return cls(
            prism_id=str(raw.get("prism_id") or ""),
            kind=str(raw.get("kind") or "content"),
            stack_path=str(path),
            lattices=tuple(rows),
            semantic_namespace=str(raw.get("semantic_namespace") or ""),
        )


def load_stack(path: str | Path) -> StackSpec:
    p = Path(path)
    return StackSpec.from_dict(p, load_config(p))
