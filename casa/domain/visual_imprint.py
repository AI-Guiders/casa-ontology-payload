#!/usr/bin/env python3
"""Visual imprint value objects (domain; wire-free)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CellPlacement:
    x: int
    y: int
    token: str


@dataclass(frozen=True)
class VisualImprintPlan:
    """RetinalCodec output: placements per lattice, shared frame identity."""

    frame_id: str
    scene_hash: str
    codec_id: str
    grid_size: int
    placements_by_lattice: dict[str, tuple[CellPlacement, ...]] = field(default_factory=dict)

    @property
    def lattice_ids(self) -> tuple[str, ...]:
        return tuple(self.placements_by_lattice.keys())

    def placement_count(self, lattice_id: str) -> int:
        return len(self.placements_by_lattice.get(lattice_id) or ())
