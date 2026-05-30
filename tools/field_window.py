#!/usr/bin/env python3
"""Tiling, ghost crops, loss masks, and overlap merge for windowed NCA on a global field."""

from __future__ import annotations

from dataclasses import dataclass

import torch

from layout_apply import Rect  # type: ignore


@dataclass(frozen=True)
class Tile:
    """Axis-aligned window on the field (interior; ghost is added at crop time)."""

    x0: int
    y0: int
    w: int
    h: int
    tile_id: str = ""

    @property
    def x1(self) -> int:
        return self.x0 + self.w - 1

    @property
    def y1(self) -> int:
        return self.y0 + self.h - 1

    def to_rect(self) -> Rect:
        return Rect(x0=self.x0, y0=self.y0, x1=self.x1, y1=self.y1)


def tiles_over_rect(
    rect: Rect,
    *,
    tile_w: int,
    tile_h: int,
    stride_x: int,
    stride_y: int,
) -> list[Tile]:
    """Enumerate overlapping tiles covering ``rect`` (inclusive bounds)."""
    if tile_w < 1 or tile_h < 1:
        raise ValueError("tile_w and tile_h must be positive")
    if stride_x < 1 or stride_y < 1:
        raise ValueError("stride must be positive")

    region_w = rect.x1 - rect.x0 + 1
    region_h = rect.y1 - rect.y0 + 1
    tiles: list[Tile] = []
    tid = 0
    y = rect.y0
    while y <= rect.y1:
        x = rect.x0
        tw = min(tile_w, region_w)
        th = min(tile_h, region_h)
        while x <= rect.x1:
            tiles.append(Tile(x0=x, y0=y, w=tw, h=th, tile_id=f"t{tid}"))
            tid += 1
            if x + tw >= rect.x1 + 1:
                break
            x += stride_x
        if y + th >= rect.y1 + 1:
            break
        y += stride_y
    return tiles


def crop_canvas_size(tile_w: int, tile_h: int, ghost: int) -> tuple[int, int]:
    """Fixed H,W for batched GPU windows (tile interior + ghost margin)."""
    return tile_h + 2 * ghost, tile_w + 2 * ghost


def extract_window_crop(
    x: torch.Tensor,
    tile: Tile,
    ghost: int,
    *,
    canvas_h: int | None = None,
    canvas_w: int | None = None,
) -> tuple[torch.Tensor, int, int]:
    """
    Copy field data into a fixed-size canvas [K, canvas_h, canvas_w] (zero-padded).

    Returns (crop, field_x0, field_y0) where field_x0/y0 is the canvas origin on the field.
    """
    if x.dim() != 3:
        raise ValueError("expected [K,H,W]")
    canvas_h = canvas_h if canvas_h is not None else tile.h + 2 * ghost
    canvas_w = canvas_w if canvas_w is not None else tile.w + 2 * ghost
    field_h, field_w = int(x.shape[-2]), int(x.shape[-1])
    out = torch.zeros(x.shape[0], canvas_h, canvas_w, device=x.device, dtype=x.dtype)
    fx0 = tile.x0 - ghost
    fy0 = tile.y0 - ghost
    src_y0 = max(0, fy0)
    src_x0 = max(0, fx0)
    src_y1 = min(field_h, tile.y0 + tile.h + ghost)
    src_x1 = min(field_w, tile.x0 + tile.w + ghost)
    dst_y0 = src_y0 - fy0
    dst_x0 = src_x0 - fx0
    dst_y1 = dst_y0 + (src_y1 - src_y0)
    dst_x1 = dst_x0 + (src_x1 - src_x0)
    if src_y1 > src_y0 and src_x1 > src_x0:
        out[:, dst_y0:dst_y1, dst_x0:dst_x1] = x[:, src_y0:src_y1, src_x0:src_x1]
    return out, fx0, fy0


def loss_mask_padded(
    canvas_h: int,
    canvas_w: int,
    tile: Tile,
    field_x0: int,
    field_y0: int,
    device: torch.device,
) -> torch.Tensor:
    """Loss mask [1,1,canvas_h,canvas_w] for tile interior on a padded crop."""
    mask = torch.zeros(1, 1, canvas_h, canvas_w, device=device)
    ix0 = tile.x0 - field_x0
    iy0 = tile.y0 - field_y0
    mask[:, :, iy0 : iy0 + tile.h, ix0 : ix0 + tile.w] = 1.0
    return mask


def crop_with_ghost(
    x: torch.Tensor,
    tile: Tile,
    ghost: int,
) -> tuple[torch.Tensor, int, int]:
    """
    Crop ``x`` [K,H,W] or [B,K,H,W] with ghost margin (clipped to field).

    Returns (crop, crop_origin_x, crop_origin_y) in field coordinates.
    """
    if x.dim() not in (3, 4):
        raise ValueError("expected [K,H,W] or [B,K,H,W]")
    h, w = int(x.shape[-2]), int(x.shape[-1])
    y0 = max(0, tile.y0 - ghost)
    x0 = max(0, tile.x0 - ghost)
    y1 = min(h, tile.y0 + tile.h + ghost)
    x1 = min(w, tile.x0 + tile.w + ghost)
    return x[..., y0:y1, x0:x1].clone(), x0, y0


def loss_mask_for_tile(
    crop_h: int,
    crop_w: int,
    tile: Tile,
    crop_origin_x: int,
    crop_origin_y: int,
    device: torch.device,
) -> torch.Tensor:
    """Mask [1,1,crop_h,crop_w] — 1 on tile interior, 0 on ghost-only border."""
    mask = torch.zeros(1, 1, crop_h, crop_w, device=device)
    ix0 = tile.x0 - crop_origin_x
    iy0 = tile.y0 - crop_origin_y
    mask[:, :, iy0 : iy0 + tile.h, ix0 : ix0 + tile.w] = 1.0
    return mask


def tile_density(tgt: torch.Tensor, tile: Tile) -> float:
    """Mean token activation in tile interior ([K,H,W])."""
    slab = tgt[:, tile.y0 : tile.y0 + tile.h, tile.x0 : tile.x0 + tile.w]
    if slab.numel() == 0:
        return 0.0
    return float(slab.mean().item())


def merge_weight_map(tile: Tile, crop_h: int, crop_w: int, crop_origin_x: int, crop_origin_y: int, device: torch.device) -> torch.Tensor:
    """
    Soft weights [1,1,crop_h,crop_w] for overlap blend — higher at tile center.
    """
    yy, xx = torch.meshgrid(
        torch.arange(crop_h, device=device, dtype=torch.float32),
        torch.arange(crop_w, device=device, dtype=torch.float32),
        indexing="ij",
    )
    cx = (tile.x0 + tile.w * 0.5) - crop_origin_x
    cy = (tile.y0 + tile.h * 0.5) - crop_origin_y
    dist = torch.sqrt((xx - cx).pow(2) + (yy - cy).pow(2) + 1e-6)
    max_d = max(tile.w, tile.h) * 0.5 + 1e-3
    w = (1.0 - (dist / max_d).clamp(0.0, 1.0)).clamp(min=1e-3)
    ix0 = tile.x0 - crop_origin_x
    iy0 = tile.y0 - crop_origin_y
    border = torch.zeros_like(w)
    border[iy0 : iy0 + tile.h, ix0 : ix0 + tile.w] = 1.0
    return (w * border).view(1, 1, crop_h, crop_w)


def paste_crop_blended(
    accum: torch.Tensor,
    weight: torch.Tensor,
    pred: torch.Tensor,
    tile: Tile,
    crop_origin_x: int,
    crop_origin_y: int,
    blend: torch.Tensor,
) -> None:
    """
    Add ``pred`` token channels into global ``accum`` / ``weight`` ([K,H,W]).
    ``pred`` and ``blend`` are crop-sized; only tile interior is written.
    """
    token_channels, ch, cw = pred.shape[0], pred.shape[-2], pred.shape[-1]
    ix0 = tile.x0 - crop_origin_x
    iy0 = tile.y0 - crop_origin_y
    gy0, gx0 = tile.y0, tile.x0
    accum[:, gy0 : gy0 + tile.h, gx0 : gx0 + tile.w] += pred[:, iy0 : iy0 + tile.h, ix0 : ix0 + tile.w] * blend[
        :, iy0 : iy0 + tile.h, ix0 : ix0 + tile.w
    ]
    weight[:, gy0 : gy0 + tile.h, gx0 : gx0 + tile.w] += blend[:, iy0 : iy0 + tile.h, ix0 : ix0 + tile.w]
