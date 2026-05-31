#!/usr/bin/env python3
"""CUDA-friendly defaults for NCA training (batch, AMP, fast grid tensors)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import random
from dataclasses import dataclass

import torch

from casa.prisms.shared.layout_apply import Rect


def add_device_args(p: argparse.ArgumentParser, *, default_batch: int | None = None) -> None:
    p.add_argument(
        "--device",
        choices=["auto", "cuda", "cpu"],
        default="auto",
        help="Training device (auto: cuda if available).",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=default_batch if default_batch is not None else 0,
        help="Batch size (0 = auto: 24 on CUDA for ~8GB VRAM, 8 on CPU).",
    )
    p.add_argument("--amp", dest="amp", action="store_true", default=None, help="Mixed precision on CUDA.")
    p.add_argument("--no-amp", dest="amp", action="store_false", help="Disable AMP.")


def resolve_train_device(device: str) -> torch.device:
    if device == "cpu":
        return torch.device("cpu")
    if device == "cuda":
        if not torch.cuda.is_available():
            raise SystemExit("CUDA requested but torch.cuda.is_available() is False")
        return torch.device("cuda")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def configure_cuda(device: torch.device) -> None:
    if device.type != "cuda":
        return
    torch.backends.cudnn.benchmark = True
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True


def _default_cuda_batch() -> int:
    try:
        from casa.prisms.shared.nca_train_defaults_v0 import cuda_batch_size_full

        return cuda_batch_size_full()
    except Exception:
        return 24


def resolve_batch_size(requested: int, device: torch.device) -> int:
    if requested > 0:
        return requested
    return _default_cuda_batch() if device.type == "cuda" else 8


def resolve_windows_per_batch(
    requested: int,
    device: torch.device,
    *,
    crop_h: int,
    crop_w: int,
    monolith_batch: int | None = None,
    max_windows: int | None = None,
) -> int:
    if monolith_batch is None:
        monolith_batch = _default_cuda_batch()
    if max_windows is None:
        try:
            from casa.prisms.shared.nca_train_defaults_v0 import load_nca_train_defaults

            max_windows = int(load_nca_train_defaults()["windowed"]["max_windows_per_batch"])
        except Exception:
            max_windows = 32
    """Auto window batch: smaller crops → more parallel windows on GPU (capped for 8GB)."""
    if requested > 0:
        return requested
    if device.type != "cuda":
        return 16
    scale = (64 * 64) / max(crop_h * crop_w, 1)
    # ~0.55 — 8GB laptop: B=64 saturated VRAM and was slower than B=24 serial
    return max(16, min(int(monolith_batch * scale * 0.55), max_windows))


def empty_cuda_cache(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.empty_cache()


def resolve_amp(use_amp: bool | None, device: torch.device) -> bool:
    if use_amp is None:
        return device.type == "cuda"
    return use_amp and device.type == "cuda"


@dataclass(frozen=True)
class GridIndex:
    """Sparse (channel, y, x) placements for one encoded grid."""

    channel: torch.Tensor
    y: torch.Tensor
    x: torch.Tensor

    @property
    def empty(self) -> bool:
        return self.channel.numel() == 0


def grid_indices(grid: dict, token_to_i: dict[str, int]) -> GridIndex:
    w = int(grid["width"])
    ch: list[int] = []
    ys: list[int] = []
    xs: list[int] = []
    for idx, cell in enumerate(grid["cells"]):
        y, x = idx // w, idx % w
        for t in cell:
            j = token_to_i.get(t)
            if j is not None:
                ch.append(j)
                ys.append(y)
                xs.append(x)
    if not ch:
        return GridIndex(
            channel=torch.empty(0, dtype=torch.long),
            y=torch.empty(0, dtype=torch.long),
            x=torch.empty(0, dtype=torch.long),
        )
    return GridIndex(
        channel=torch.tensor(ch, dtype=torch.long),
        y=torch.tensor(ys, dtype=torch.long),
        x=torch.tensor(xs, dtype=torch.long),
    )


def scatter_grid_tensor(
    idx: GridIndex,
    *,
    token_channels: int,
    h: int,
    w: int,
    device: torch.device,
    batch: int = 1,
) -> torch.Tensor:
    x = torch.zeros(batch, token_channels, h, w, device=device)
    if not idx.empty:
        x[0, idx.channel.to(device), idx.y.to(device), idx.x.to(device)] = 1.0
    return x


def scatter_batch_from_indices(
    indices: list[GridIndex],
    *,
    token_channels: int,
    h: int,
    w: int,
    device: torch.device,
) -> torch.Tensor:
    b = len(indices)
    x = torch.zeros(b, token_channels, h, w, device=device)
    for bi, idx in enumerate(indices):
        if idx.empty:
            continue
        x[bi, idx.channel.to(device), idx.y.to(device), idx.x.to(device)] = 1.0
    return x


def print_train_device(device: torch.device, batch_size: int, amp: bool) -> None:
    if device.type == "cuda":
        name = torch.cuda.get_device_name(device)
        print(f"train_device=cuda ({name}) batch_size={batch_size} amp={amp}")
    else:
        print(f"train_device=cpu batch_size={batch_size} amp=False")


def damage_tensor_patches(
    tgt: torch.Tensor,
    rect: Rect,
    *,
    patch_w: int,
    patch_h: int,
    count: int,
    seed: int,
    module_mask: torch.Tensor | None = None,
) -> torch.Tensor:
    """
    Zero token activations in random patches (GPU-friendly).

    tgt: [K,H,W] or [B,K,H,W]
    module_mask: optional [H,W] — patch anchors prefer cells where mask > 0
    """
    if tgt.dim() == 3:
        out = tgt.clone()
        _damage_tensor_patches_inplace(out, rect, patch_w=patch_w, patch_h=patch_h, count=count, seed=seed, module_mask=module_mask)
        return out
    out = tgt.clone()
    for b in range(out.shape[0]):
        m = module_mask
        if module_mask is not None and module_mask.dim() == 3:
            m = module_mask[b]
        _damage_tensor_patches_inplace(
            out[b], rect, patch_w=patch_w, patch_h=patch_h, count=count, seed=seed + b * 131, module_mask=m
        )
    return out


def _damage_tensor_patches_inplace(
    tgt: torch.Tensor,
    rect: Rect,
    *,
    patch_w: int,
    patch_h: int,
    count: int,
    seed: int,
    module_mask: torch.Tensor | None,
) -> None:
    h, w = int(tgt.shape[-2]), int(tgt.shape[-1])
    rng = random.Random(seed)
    patch_w = max(1, min(patch_w, rect.x1 - rect.x0 + 1, w))
    patch_h = max(1, min(patch_h, rect.y1 - rect.y0 + 1, h))

    anchors: list[tuple[int, int]] = []
    if module_mask is not None:
        ys, xs = torch.where(module_mask > 0)
        anchors = [(int(y), int(x)) for y, x in zip(ys.tolist(), xs.tolist(), strict=False)]

    for _ in range(count):
        if anchors:
            ay, ax = anchors[rng.randrange(len(anchors))]
            x0 = max(rect.x0, min(ax - patch_w // 2, rect.x1 - patch_w + 1))
            y0 = max(rect.y0, min(ay - patch_h // 2, rect.y1 - patch_h + 1))
        else:
            x0 = rng.randint(rect.x0, rect.x1 - patch_w + 1)
            y0 = rng.randint(rect.y0, rect.y1 - patch_h + 1)
        tgt[:, y0 : y0 + patch_h, x0 : x0 + patch_w] = 0.0
