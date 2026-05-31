#!/usr/bin/env python3
"""Sliding-window NCA repair: batched rollout per tiles, merge with overlap weights."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import torch

from casa.prisms.shared.field_planner import FieldPlannerV0
from casa.prisms.shared.field_window import (
    crop_canvas_size,
    crop_with_ghost,
    extract_window_crop,
    merge_weight_map,
    paste_crop_blended,
)
from casa.prisms.shared.layout_apply import Rect
from casa.prisms.shared.nca_train_util import damage_tensor_patches
from casa.cli.train_dmn_nca import UpdateRule, nca_rollout_eval, sobel_kernels


def repair_field_windowed(
    rule: UpdateRule,
    tgt: torch.Tensor,
    planner: FieldPlannerV0,
    *,
    token_channels: int,
    channel_n: int,
    kx: torch.Tensor,
    ky: torch.Tensor,
    steps: int,
    ghost: int,
    device: torch.device,
    damage_seed: int,
    damage_patches: int,
    patch_w: int,
    patch_h: int,
    tile_w: int = 32,
    tile_h: int = 32,
    batched: bool = True,
) -> torch.Tensor:
    """Damage full field, repair by tiles, return token channels [K,H,W]."""
    h, w = int(tgt.shape[-2]), int(tgt.shape[-1])
    if not planner.tiles:
        return tgt.clone()

    x0 = min(t.x0 for t in planner.tiles)
    y0 = min(t.y0 for t in planner.tiles)
    x1 = max(t.x1 for t in planner.tiles)
    y1 = max(t.y1 for t in planner.tiles)
    region = Rect(x0=x0, y0=y0, x1=x1, y1=y1)
    damaged = damage_tensor_patches(
        tgt,
        region,
        patch_w=patch_w,
        patch_h=patch_h,
        count=damage_patches,
        seed=damage_seed,
    )

    tiles = planner.repair_order()
    if batched and len(tiles) > 1:
        return _repair_batched(
            rule,
            damaged,
            tiles,
            token_channels=token_channels,
            channel_n=channel_n,
            kx=kx,
            ky=ky,
            steps=steps,
            ghost=ghost,
            device=device,
            tile_w=tile_w,
            tile_h=tile_h,
        )
    return _repair_serial(
        rule,
        damaged,
        tiles,
        token_channels=token_channels,
        channel_n=channel_n,
        kx=kx,
        ky=ky,
        steps=steps,
        ghost=ghost,
        device=device,
    )


def _repair_serial(
    rule: UpdateRule,
    damaged: torch.Tensor,
    tiles: list,
    *,
    token_channels: int,
    channel_n: int,
    kx: torch.Tensor,
    ky: torch.Tensor,
    steps: int,
    ghost: int,
    device: torch.device,
) -> torch.Tensor:
    h, w = int(damaged.shape[-2]), int(damaged.shape[-1])
    accum = torch.zeros(token_channels, h, w, device=device)
    weight = torch.zeros(1, h, w, device=device)

    for tile in tiles:
        crop_d, ox, oy = crop_with_ghost(damaged, tile, ghost)
        ch, cw = crop_d.shape[-2], crop_d.shape[-1]
        x = torch.zeros(1, channel_n, ch, cw, device=device)
        x[:, :token_channels] = crop_d.unsqueeze(0)
        xT = nca_rollout_eval(rule, x, kx, ky, steps=steps)
        pred = xT[0, :token_channels]
        blend = merge_weight_map(tile, ch, cw, ox, oy, device)[0]
        paste_crop_blended(accum, weight, pred, tile, ox, oy, blend)

    return _blend_output(damaged, accum, weight)


def _repair_batched(
    rule: UpdateRule,
    damaged: torch.Tensor,
    tiles: list,
    *,
    token_channels: int,
    channel_n: int,
    kx: torch.Tensor,
    ky: torch.Tensor,
    steps: int,
    ghost: int,
    device: torch.device,
    tile_w: int,
    tile_h: int,
) -> torch.Tensor:
    h, w = int(damaged.shape[-2]), int(damaged.shape[-1])
    canvas_h, canvas_w = crop_canvas_size(tile_w, tile_h, ghost)
    meta: list[tuple] = []
    crops: list[torch.Tensor] = []
    for tile in tiles:
        crop_d, fx0, fy0 = extract_window_crop(
            damaged,
            tile,
            ghost,
            canvas_h=canvas_h,
            canvas_w=canvas_w,
        )
        crops.append(crop_d)
        meta.append((tile, fx0, fy0))

    batch = torch.stack(crops, dim=0)
    x = torch.zeros(batch.shape[0], channel_n, canvas_h, canvas_w, device=device)
    x[:, :token_channels] = batch
    xT = nca_rollout_eval(rule, x, kx, ky, steps=steps)

    accum = torch.zeros(token_channels, h, w, device=device)
    weight = torch.zeros(1, h, w, device=device)
    for i, (tile, fx0, fy0) in enumerate(meta):
        pred = xT[i, :token_channels]
        blend = merge_weight_map(tile, canvas_h, canvas_w, fx0, fy0, device)[0]
        paste_crop_blended(accum, weight, pred, tile, fx0, fy0, blend)

    return _blend_output(damaged, accum, weight)


def _blend_output(damaged: torch.Tensor, accum: torch.Tensor, weight: torch.Tensor) -> torch.Tensor:
    out = damaged.clone()
    nz = weight > 1e-6
    out[:, nz[0]] = accum[:, nz[0]] / weight[nz]
    return out.clamp(0.0, 1.0)
