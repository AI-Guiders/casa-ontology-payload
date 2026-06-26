#!/usr/bin/env python3
"""Auditory imprint value objects (domain; wire-free)."""

from __future__ import annotations

from dataclasses import dataclass, field

from casa.domain.visual_imprint import CellPlacement


@dataclass(frozen=True)
class AuditoryImprintPlan:
    """CochlearCodec output: temporal-spectral placements on auditory lattice."""

    window_id: str
    scene_id: str
    audio_hash: str
    codec_id: str
    grid_size: int
    sample_rate: int
    duration_ms: int
    placements_by_lattice: dict[str, tuple[CellPlacement, ...]] = field(default_factory=dict)

    @property
    def lattice_ids(self) -> tuple[str, ...]:
        return tuple(self.placements_by_lattice.keys())

    def placement_count(self, lattice_id: str) -> int:
        return len(self.placements_by_lattice.get(lattice_id) or ())
