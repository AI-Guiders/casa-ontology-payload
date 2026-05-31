#!/usr/bin/env python3
"""NCA rollout repair on damaged SSS lattice."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.prisms.shared.prism_state_v0 import normalize_prisms, prism_memory, prism_hippo, prism_control, PRISM_MEMORY, PRISM_HIPPO, PRISM_CONTROL, set_active_prism
import copy
from pathlib import Path
from typing import Any

import numpy as np
import torch

from casa.prisms.shared.layout_apply import Rect
from casa.prisms.shared.nca_train_util import damage_tensor_patches, grid_indices, scatter_grid_tensor
from casa.prisms.hippo.sss_damage_v0 import damage_lattice
from casa.prisms.memory.sss_nca_codec_v0 import grid_to_lattice_cells, lattice_as_grid, tokens_from_lattice, word_tokens_from_lattice
from casa.cli.train_dmn_nca import UpdateRule, nca_rollout_eval, sobel_kernels


def _load_model(path: Path) -> dict[str, Any]:
    return torch.load(path, map_location="cpu", weights_only=False)


def _threshold_grid(state: torch.Tensor, token_ids: list[str], threshold: float = 0.5) -> dict:
    token_count = len(token_ids)
    x = state[0, :token_count].detach().cpu().numpy()
    x = np.clip(x, 0.0, 1.0)
    h, w = x.shape[1], x.shape[2]
    cells: list[list[str]] = [[] for _ in range(w * h)]
    for yi in range(h):
        for xi in range(w):
            idx = yi * w + xi
            on = np.where(x[:, yi, xi] >= threshold)[0]
            if on.size:
                cells[idx] = [token_ids[int(j)] for j in on]
    return {"schema_version": 1, "width": w, "height": h, "cells": cells}


def nca_repair_lattice(
    lattice: dict,
    model_path: Path,
    *,
    damage_patches: int = 4,
    patch_w: int = 8,
    patch_h: int = 8,
    seed: int = 42,
    threshold: float = 0.5,
    device: str = "cpu",
) -> dict[str, Any]:
    ckpt = _load_model(model_path)
    token_ids: list[str] = list(ckpt["token_ids"])
    token_count = len(token_ids)
    channel_n = int(ckpt["channel_n"])
    steps = int(ckpt.get("steps") or 24)
    hidden = int(ckpt.get("hidden") or 96)

    damaged = damage_lattice(
        lattice,
        patch_w=patch_w,
        patch_h=patch_h,
        count=damage_patches,
        seed=seed,
    )
    grid = lattice_as_grid(damaged)
    h = int(grid["height"])
    w = int(grid["width"])
    rect = Rect(x0=0, y0=0, x1=w - 1, y1=h - 1)
    token_to_i = {t: i for i, t in enumerate(token_ids)}
    inp_tok = scatter_grid_tensor(
        grid_indices(grid, token_to_i), token_channels=token_count, h=h, w=w, device=torch.device(device)
    )[0]

    dev = torch.device(device)
    rule = UpdateRule(channel_n=channel_n, hidden=hidden)
    rule.load_state_dict(ckpt["state_dict"])
    rule.to(dev)
    rule.eval()

    kx, ky = sobel_kernels(dev)
    seed_t = torch.zeros(1, channel_n, h, w, device=dev)
    seed_t[:, :token_count] = inp_tok.unsqueeze(0)
    with torch.no_grad():
        out = nca_rollout_eval(rule, seed_t, kx, ky, steps)
    repaired_grid = _threshold_grid(out, token_ids, threshold=threshold)

    w_before = len(word_tokens_from_lattice(lattice))
    w_damaged = len(word_tokens_from_lattice(damaged))
    w_repaired = sum(1 for cell in repaired_grid["cells"] for t in cell if t.startswith("W:"))

    out_lat = copy.deepcopy(lattice)
    out_lat["cells"] = grid_to_lattice_cells(repaired_grid, token_filter=set(token_ids))
    out_lat["nca_repair"] = {
        "model": str(model_path),
        "seed": seed,
        "w_before": w_before,
        "w_damaged": w_damaged,
        "w_repaired_grid": w_repaired,
    }
    return {
        "lattice": out_lat,
        "damage": damaged.get("damage"),
        "w_before": w_before,
        "w_damaged": w_damaged,
        "w_repaired": w_repaired,
        "recovery_ratio": round(w_repaired / max(1, w_before), 3),
    }


def nca_regrow_lattice(
    lattice: dict,
    model_path: Path,
    *,
    threshold: float = 0.5,
    device: str = "cpu",
) -> dict[str, Any]:
    """Sleep regrowth: rollout from current lattice (no intentional damage)."""
    ckpt = _load_model(model_path)
    token_ids: list[str] = list(ckpt["token_ids"])
    token_count = len(token_ids)
    channel_n = int(ckpt["channel_n"])
    steps = int(ckpt.get("steps") or 24)
    hidden = int(ckpt.get("hidden") or 96)

    grid = lattice_as_grid(lattice)
    h = int(grid["height"])
    w = int(grid["width"])
    token_to_i = {t: i for i, t in enumerate(token_ids)}
    inp_tok = scatter_grid_tensor(
        grid_indices(grid, token_to_i), token_channels=token_count, h=h, w=w, device=torch.device(device)
    )[0]

    dev = torch.device(device)
    rule = UpdateRule(channel_n=channel_n, hidden=hidden)
    rule.load_state_dict(ckpt["state_dict"])
    rule.to(dev)
    rule.eval()

    kx, ky = sobel_kernels(dev)
    seed_t = torch.zeros(1, channel_n, h, w, device=dev)
    seed_t[:, :token_count] = inp_tok.unsqueeze(0)
    with torch.no_grad():
        out = nca_rollout_eval(rule, seed_t, kx, ky, steps)
    regrown = _threshold_grid(out, token_ids, threshold=threshold)

    w_before = len(word_tokens_from_lattice(lattice))
    out_lat = copy.deepcopy(lattice)
    out_lat["cells"] = grid_to_lattice_cells(regrown, token_filter=set(token_ids))
    w_after = sum(1 for cell in regrown["cells"] for t in cell if t.startswith("W:"))
    return {
        "lattice": out_lat,
        "w_before": w_before,
        "w_after": w_after,
        "mode": "regrow",
    }


def nca_repair_state_lattice(
    state: dict,
    lattice_id: str,
    model_path: Path,
    *,
    damage_patches: int = 4,
    seed: int = 42,
    device: str = "cpu",
) -> dict[str, Any]:
    from casa.prisms.memory.sss_cylinders_v0 import memory_lattices

    lattices = memory_lattices(state)
    lat = lattices.get(lattice_id)
    if not lat:
        raise KeyError(lattice_id)
    rep = nca_repair_lattice(
        lat,
        model_path,
        damage_patches=damage_patches,
        seed=seed,
        device=device,
    )
    lattices[lattice_id] = rep["lattice"]
    prism_memory(state)["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices
    state.setdefault("nca", {})["last_repair"] = {key: val for key, val in rep.items() if key != "lattice"}
    return rep
