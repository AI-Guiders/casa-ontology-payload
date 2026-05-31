#!/usr/bin/env python3
"""
Shared NCA recovery training loop (full-field and windowed).

DMN bundles and SSS lattices differ only in how the target tensor [K,H,W] is built;
physics (UpdateRule, rollout, damage, AMP) is identical.
"""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from dataclasses import dataclass, field
from typing import Literal

import torch
import torch.nn as nn

from casa.prisms.shared.field_planner_v0 import FieldPlannerV0
from casa.prisms.shared.field_window import crop_canvas_size, extract_window_crop, loss_mask_padded
from casa.prisms.shared.layout_apply import Rect
from casa.prisms.shared.nca_train_util import (
    configure_cuda,
    damage_tensor_patches,
    empty_cuda_cache,
    print_train_device,
    resolve_amp,
    resolve_batch_size,
    resolve_train_device,
    resolve_windows_per_batch,
)
from casa.cli.train_dmn_nca import UpdateRule, nca_rollout, sobel_kernels

TrainMode = Literal["full", "windowed"]


def edge_token_weights(
    token_ids: list[str],
    edge_weight: float,
    device: torch.device,
    *,
    prefix: str = "E:",
) -> torch.Tensor | None:
    if edge_weight == 1.0:
        return None
    w = torch.ones(len(token_ids), device=device)
    for i, t in enumerate(token_ids):
        if t.startswith(prefix):
            w[i] = float(edge_weight)
    return w.view(1, len(token_ids), 1, 1)


@dataclass
class NcaTrainerConfig:
    token_channels: int
    h: int
    w: int
    hidden: int = 96
    channel_extra: int = 6
    steps: int = 24
    epochs: int = 80
    lr: float = 2e-4
    fire_rate: float = 0.5
    damage_patches: int = 4
    patch_w: int = 8
    patch_h: int = 8
    seed: int = 1
    device: str = "auto"
    batch_size: int = 0
    amp: bool | None = None
    grad_clip: float = 1.0
    log_every: int = 50

    @property
    def channel_n(self) -> int:
        return self.token_channels + self.channel_extra


@dataclass
class WindowedTrainConfig:
    tile_w: int = 16
    tile_h: int = 16
    stride_x: int = 8
    stride_y: int = 8
    ghost: int = 2
    windows_per_batch: int = 0
    max_windows_per_batch: int = 32
    edge_weight: float = 1.0


@dataclass
class TrainRunResult:
    best_loss: float
    state_dict: dict
    mode: TrainMode
    batch_size: int
    windows_per_batch: int = 0


@dataclass
class _TrainerRuntime:
    device: torch.device
    use_amp: bool
    rule: UpdateRule
    opt: torch.optim.Optimizer
    scaler: torch.amp.GradScaler
    kx: torch.Tensor
    ky: torch.Tensor
    best_loss: float = field(default=float("inf"))
    best_state: dict | None = None


def _build_runtime(cfg: NcaTrainerConfig) -> _TrainerRuntime:
    device = resolve_train_device(cfg.device)
    configure_cuda(device)
    use_amp = resolve_amp(cfg.amp, device)
    rule = UpdateRule(channel_n=cfg.channel_n, hidden=cfg.hidden).to(device)
    opt = torch.optim.Adam(rule.parameters(), lr=cfg.lr)
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    kx, ky = sobel_kernels(device)
    return _TrainerRuntime(device=device, use_amp=use_amp, rule=rule, opt=opt, scaler=scaler, kx=kx, ky=ky)


def _maybe_save_best(rt: _TrainerRuntime, loss_val: float) -> None:
    if loss_val < rt.best_loss:
        rt.best_loss = loss_val
        rt.best_state = {kk: v.detach().clone() for kk, v in rt.rule.state_dict().items()}


def train_epoch_full_field(
    rt: _TrainerRuntime,
    cfg: NcaTrainerConfig,
    *,
    tgt: torch.Tensor,
    rect: Rect,
    epoch: int,
    batch_size: int,
) -> float:
    """One optimizer step on full [K,H,W] (SSS lattice or DMN monolith)."""
    batch_inp: list[torch.Tensor] = []
    for b in range(batch_size):
        inp_tok = damage_tensor_patches(
            tgt,
            rect,
            patch_w=cfg.patch_w,
            patch_h=cfg.patch_h,
            count=cfg.damage_patches,
            seed=cfg.seed + epoch * 31 + b * 7,
        )
        batch_inp.append(inp_tok)
    inp = torch.stack(batch_inp, dim=0)
    tgt_b = tgt.unsqueeze(0).expand(batch_size, -1, -1, -1)
    x = torch.zeros(batch_size, cfg.channel_n, cfg.h, cfg.w, device=rt.device)
    x[:, : cfg.token_channels] = inp

    rt.opt.zero_grad(set_to_none=True)
    with torch.autocast(device_type=rt.device.type, enabled=rt.use_amp):
        x = nca_rollout(rt.rule, x, rt.kx, rt.ky, cfg.steps, cfg.fire_rate)
        loss = nn.functional.mse_loss(x[:, : cfg.token_channels], tgt_b)

    rt.scaler.scale(loss).backward()
    rt.scaler.unscale_(rt.opt)
    torch.nn.utils.clip_grad_norm_(rt.rule.parameters(), cfg.grad_clip)
    rt.scaler.step(rt.opt)
    rt.scaler.update()
    return float(loss.item())


def train_epoch_windowed(
    rt: _TrainerRuntime,
    cfg: NcaTrainerConfig,
    win: WindowedTrainConfig,
    *,
    tgt: torch.Tensor,
    rect: Rect,
    planner: FieldPlannerV0,
    epoch: int,
    windows_per_batch: int,
    canvas_h: int,
    canvas_w: int,
    token_w: torch.Tensor | None = None,
) -> float:
    """One optimizer step on parallel window crops (Exp J path)."""
    sampled = planner.sample_train_tiles(windows_per_batch, epoch=epoch, seed=cfg.seed)
    crops_t: list[torch.Tensor] = []
    crops_i: list[torch.Tensor] = []
    masks: list[torch.Tensor] = []

    for wi, tile in enumerate(sampled):
        seed = cfg.seed + epoch * 10007 + wi * 131
        damaged = damage_tensor_patches(
            tgt,
            tile.to_rect(),
            patch_w=cfg.patch_w,
            patch_h=cfg.patch_h,
            count=cfg.damage_patches,
            seed=seed,
        )
        crop_t, fx0, fy0 = extract_window_crop(tgt, tile, win.ghost, canvas_h=canvas_h, canvas_w=canvas_w)
        crop_i, _, _ = extract_window_crop(damaged, tile, win.ghost, canvas_h=canvas_h, canvas_w=canvas_w)
        crops_t.append(crop_t)
        crops_i.append(crop_i)
        masks.append(loss_mask_padded(canvas_h, canvas_w, tile, fx0, fy0, rt.device))

    rt.opt.zero_grad(set_to_none=True)
    tgt_b = torch.stack(crops_t, dim=0)
    inp_b = torch.stack(crops_i, dim=0)
    mask_b = torch.cat(masks, dim=0)
    x = torch.zeros(windows_per_batch, cfg.channel_n, canvas_h, canvas_w, device=rt.device)
    x[:, : cfg.token_channels] = inp_b

    with torch.autocast(device_type=rt.device.type, enabled=rt.use_amp):
        x = nca_rollout(rt.rule, x, rt.kx, rt.ky, cfg.steps, cfg.fire_rate)
        pred = x[:, : cfg.token_channels]
        diff = (pred - tgt_b).pow(2)
        if token_w is not None:
            diff = diff * token_w
        denom = mask_b.sum().clamp(min=1.0)
        loss = (diff * mask_b).sum() / denom

    rt.scaler.scale(loss).backward()
    rt.scaler.unscale_(rt.opt)
    torch.nn.utils.clip_grad_norm_(rt.rule.parameters(), cfg.grad_clip)
    rt.scaler.step(rt.opt)
    rt.scaler.update()
    empty_cuda_cache(rt.device)
    return float(loss.item())


def run_nca_training(
    cfg: NcaTrainerConfig,
    *,
    tgt: torch.Tensor,
    rect: Rect,
    mode: TrainMode = "full",
    windowed: WindowedTrainConfig | None = None,
    token_w: torch.Tensor | None = None,
) -> TrainRunResult:
    """
    Train recovery NCA on a target field tensor.

    tgt: [token_channels, H, W] token activations (SSS lattice or masked DMN region).
    """
    rt = _build_runtime(cfg)
    win = windowed or WindowedTrainConfig()

    if mode == "full":
        batch_size = resolve_batch_size(cfg.batch_size, rt.device)
        print_train_device(rt.device, batch_size, rt.use_amp)
        for epoch in range(cfg.epochs):
            lv = train_epoch_full_field(rt, cfg, tgt=tgt, rect=rect, epoch=epoch, batch_size=batch_size)
            _maybe_save_best(rt, lv)
            if epoch % cfg.log_every == 0 or epoch == cfg.epochs - 1:
                print(f"epoch {epoch:4d} loss={lv:.6f}")
        return TrainRunResult(
            best_loss=rt.best_loss,
            state_dict=rt.best_state or rt.rule.state_dict(),
            mode="full",
            batch_size=batch_size,
        )

    canvas_h, canvas_w = crop_canvas_size(win.tile_w, win.tile_h, win.ghost)
    win_batch = resolve_windows_per_batch(
        win.windows_per_batch,
        rt.device,
        crop_h=canvas_h,
        crop_w=canvas_w,
        max_windows=win.max_windows_per_batch,
    )
    print_train_device(rt.device, win_batch, rt.use_amp)
    print(
        f"windowed tile={win.tile_w}x{win.tile_h} stride={win.stride_x},{win.stride_y} "
        f"ghost={win.ghost} canvas={canvas_w}x{canvas_h} windows_per_batch={win_batch}"
    )

    planner = FieldPlannerV0.from_field_tensor(
        tgt,
        rect,
        tile_w=win.tile_w,
        tile_h=win.tile_h,
        stride_x=win.stride_x,
        stride_y=win.stride_y,
    )

    for epoch in range(cfg.epochs):
        lv = train_epoch_windowed(
            rt,
            cfg,
            win,
            tgt=tgt,
            rect=rect,
            planner=planner,
            epoch=epoch,
            windows_per_batch=win_batch,
            canvas_h=canvas_h,
            canvas_w=canvas_w,
            token_w=token_w,
        )
        _maybe_save_best(rt, lv)
        if epoch % cfg.log_every == 0 or epoch == cfg.epochs - 1:
            print(f"epoch {epoch:4d} loss={lv:.6f}")

    return TrainRunResult(
        best_loss=rt.best_loss,
        state_dict=rt.best_state or rt.rule.state_dict(),
        mode="windowed",
        batch_size=win_batch,
        windows_per_batch=win_batch,
    )
