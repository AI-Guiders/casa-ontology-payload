#!/usr/bin/env python3
"""Visual tract vocabulary (ADR-0028 / ADR-0020 domain SSOT)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

TRACT_VISUAL: Final = "visual"
CODEC_RETINAL_LRGB: Final = "retinal_lrgb"

LATTICE_V1_LUM: Final = "V1_lum"
LATTICE_V1_CHROM_R: Final = "V1_chrom_r"
LATTICE_V1_CHROM_G: Final = "V1_chrom_g"
LATTICE_V1_CHROM_B: Final = "V1_chrom_b"
LEGACY_LATTICE_V1_OBJECT: Final = "V1_object"

PREFIX_VIS_LUM: Final = "vis.lum."
PREFIX_VIS_CHROM_R: Final = "vis.chrom.r."
PREFIX_VIS_CHROM_G: Final = "vis.chrom.g."
PREFIX_VIS_CHROM_B: Final = "vis.chrom.b."

VISUAL_LATTICE_IDS: Final = (
    LATTICE_V1_LUM,
    LATTICE_V1_CHROM_R,
    LATTICE_V1_CHROM_G,
    LATTICE_V1_CHROM_B,
)

CHANNEL_LUM: Final = "lum"
CHANNEL_CHROM_R: Final = "r"
CHANNEL_CHROM_G: Final = "g"
CHANNEL_CHROM_B: Final = "b"

DEFAULT_GRID_SIZE: Final = 32
DEFAULT_QUANT_LEVELS: Final = 16


@dataclass(frozen=True)
class VisualLatticeSpec:
    lattice_id: str
    concept_prefix: str
    channel: str
    z_level: int = 1


VISUAL_LATTICE_SPECS: Final = (
    VisualLatticeSpec(LATTICE_V1_LUM, PREFIX_VIS_LUM, CHANNEL_LUM, z_level=0),
    VisualLatticeSpec(LATTICE_V1_CHROM_R, PREFIX_VIS_CHROM_R, CHANNEL_CHROM_R, z_level=1),
    VisualLatticeSpec(LATTICE_V1_CHROM_G, PREFIX_VIS_CHROM_G, CHANNEL_CHROM_G, z_level=1),
    VisualLatticeSpec(LATTICE_V1_CHROM_B, PREFIX_VIS_CHROM_B, CHANNEL_CHROM_B, z_level=1),
)

VISUAL_LATTICE_ID_SET: Final = frozenset(VISUAL_LATTICE_IDS) | {LEGACY_LATTICE_V1_OBJECT}


def is_visual_lattice_id(lattice_id: str) -> bool:
    return str(lattice_id or "") in VISUAL_LATTICE_ID_SET
