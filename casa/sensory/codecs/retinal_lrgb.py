#!/usr/bin/env python3
"""Retinal codec: RGB → L + R/G/B imprint (ADR-0028)."""

from __future__ import annotations

import hashlib

from casa.domain.visual_imprint import CellPlacement, VisualImprintPlan
from casa.domain.visual_tract import (
    CODEC_RETINAL_LRGB,
    DEFAULT_GRID_SIZE,
    DEFAULT_QUANT_LEVELS,
    LATTICE_V1_CHROM_B,
    LATTICE_V1_CHROM_G,
    LATTICE_V1_CHROM_R,
    LATTICE_V1_LUM,
    CHANNEL_CHROM_B,
    CHANNEL_CHROM_G,
    CHANNEL_CHROM_R,
    CHANNEL_LUM,
)
from casa.sensory.rgb_frame import RgbFrame

# ITU-R BT.601 luma (8-bit)
_LUMA_R = 0.299
_LUMA_G = 0.587
_LUMA_B = 0.114


def luminance_u8(r: int, g: int, b: int) -> int:
    return int(_LUMA_R * r + _LUMA_G * g + _LUMA_B * b + 0.5)


def quantize_u8(value: int, *, levels: int = DEFAULT_QUANT_LEVELS) -> int:
    v = max(0, min(255, int(value)))
    lv = max(2, int(levels))
    bucket = (v * lv) // 256
    return min(bucket, lv - 1)


def channel_token(channel: str, level: int) -> str:
    return f"V:{channel}:{level:02x}"


def _downsample_channel(
    frame: RgbFrame,
    *,
    grid: int,
    channel: str,
) -> list[CellPlacement]:
    out: list[CellPlacement] = []
    gw = grid
    gh = grid
    for gy in range(gh):
        for gx in range(gw):
            sx = gx * frame.width // gw
            sy = gy * frame.height // gh
            ex = max(sx + 1, (gx + 1) * frame.width // gw)
            ey = max(sy + 1, (gy + 1) * frame.height // gh)
            rs = gs = bs = 0
            n = 0
            for y in range(sy, ey):
                for x in range(sx, ex):
                    r, g, b = frame.pixel(x, y)
                    rs += r
                    gs += g
                    bs += b
                    n += 1
            if n <= 0:
                continue
            r = rs // n
            g = gs // n
            b = bs // n
            if channel == CHANNEL_LUM:
                val = luminance_u8(r, g, b)
            elif channel == CHANNEL_CHROM_R:
                val = r
            elif channel == CHANNEL_CHROM_G:
                val = g
            elif channel == CHANNEL_CHROM_B:
                val = b
            else:
                raise ValueError(channel)
            lvl = quantize_u8(val)
            out.append(CellPlacement(gx, gy, channel_token(channel, lvl)))
    return out


def encode_retinal_lrgb(
    frame: RgbFrame,
    *,
    frame_id: str | None = None,
    grid_size: int = DEFAULT_GRID_SIZE,
    levels: int = DEFAULT_QUANT_LEVELS,
) -> VisualImprintPlan:
    fid = (frame_id or "").strip() or hashlib.sha256(frame.rgb).hexdigest()[:16]
    scene_hash = hashlib.sha256(frame.rgb).hexdigest()
    _ = levels
    return VisualImprintPlan(
        frame_id=fid,
        scene_hash=scene_hash,
        codec_id=CODEC_RETINAL_LRGB,
        grid_size=grid_size,
        placements_by_lattice={
            LATTICE_V1_LUM: tuple(_downsample_channel(frame, grid=grid_size, channel=CHANNEL_LUM)),
            LATTICE_V1_CHROM_R: tuple(_downsample_channel(frame, grid=grid_size, channel=CHANNEL_CHROM_R)),
            LATTICE_V1_CHROM_G: tuple(_downsample_channel(frame, grid=grid_size, channel=CHANNEL_CHROM_G)),
            LATTICE_V1_CHROM_B: tuple(_downsample_channel(frame, grid=grid_size, channel=CHANNEL_CHROM_B)),
        },
    )
