#!/usr/bin/env python3
"""Agent lattice NCA training — split from agent_prism persist layer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch

from casa.prisms.shared.layout_apply import Rect
from casa.prisms.shared.nca_train_core import NcaTrainerConfig, WindowedTrainConfig, run_nca_training
from casa.prisms.shared.nca_train_defaults import damage_defaults, epoch_budget, field_edge, nca_profile
from casa.prisms.shared.nca_train_util import damage_tensor_patches, grid_indices, resolve_train_device, scatter_grid_tensor
from casa.prisms.shared.store_layout import agent_nca_lattice_dir
from casa.cli.train_dmn_nca import UpdateRule, nca_rollout_eval, sobel_kernels
from casa.prisms.memory.agent_prism import agent_lattices, ensure_agent_prism, safe_agent_lattice_id
from casa.prisms.memory.nca_codec import lattice_as_grid, tokens_from_lattice


def train_agent_lattice_nca(
    state: dict,
    store_dir: Path,
    lattice_id: str,
    *,
    epochs: int | None = None,
    device: str = "auto",
    seed: int = 1,
) -> dict[str, Any]:
    lid = safe_agent_lattice_id(lattice_id)
    lats = agent_lattices(state)
    if lid not in lats:
        raise KeyError(f"unknown agent lattice: {lid}")
    lattice = lats[lid]

    token_ids = tokens_from_lattice(lattice)
    if not token_ids:
        raise ValueError(f"lattice {lid} has no tokens to train on")

    profile = nca_profile("sss")
    dmg = damage_defaults()
    fe = field_edge("sss_lattice")
    ep = epoch_budget("sss_shard_incremental") if epochs is None else int(epochs)

    torch.manual_seed(seed)
    np.random.seed(seed)
    dev = resolve_train_device(device)

    grid = lattice_as_grid(lattice)
    token_count = len(token_ids)
    channel_n = token_count + 6
    h = int(grid["height"])
    w = int(grid["width"])
    rect = Rect(x0=0, y0=0, x1=w - 1, y1=h - 1)
    token_to_i = {t: i for i, t in enumerate(token_ids)}
    tgt_tok = scatter_grid_tensor(grid_indices(grid, token_to_i), token_channels=token_count, h=h, w=w, device=dev)[0]

    train_cfg = NcaTrainerConfig(
        token_channels=token_count,
        h=h,
        w=w,
        hidden=int(profile["hidden"]),
        channel_extra=6,
        steps=int(profile["steps"]),
        epochs=ep,
        lr=float(profile["lr"]),
        fire_rate=float(profile["fire_rate"]),
        damage_patches=int(dmg["damage_patches"]),
        patch_w=int(dmg["patch_w"]),
        patch_h=int(dmg["patch_h"]),
        seed=seed,
        device=device,
    )
    win_cfg = WindowedTrainConfig(
        tile_w=fe["tile_w"],
        tile_h=fe["tile_h"],
        stride_x=fe["stride_x"],
        stride_y=fe["stride_y"],
        ghost=fe["ghost"],
        windows_per_batch=fe["windows_per_batch"],
        max_windows_per_batch=fe["max_windows_per_batch"],
        edge_weight=fe["edge_weight"],
    )
    run = run_nca_training(train_cfg, tgt=tgt_tok, rect=rect, mode="windowed", windowed=win_cfg)
    rule = UpdateRule(channel_n=channel_n, hidden=int(profile["hidden"])).to(dev)
    rule.load_state_dict(run.state_dict)

    out_dir = agent_nca_lattice_dir(store_dir, lid)
    out_dir.mkdir(parents=True, exist_ok=True)
    model_path = out_dir / "model.pt"
    torch.save(
        {
            "schema_version": 1,
            "kind": "agent_lattice_nca",
            "lattice_id": lid,
            "channel_n": channel_n,
            "token_ids": token_ids,
            "width": w,
            "height": h,
            "hidden": int(profile["hidden"]),
            "steps": int(profile["steps"]),
            "fire_rate_train": float(profile["fire_rate"]),
            "state_dict": rule.state_dict(),
        },
        model_path,
    )

    kx, ky = sobel_kernels(dev)
    with torch.no_grad():
        eval_inp = damage_tensor_patches(
            tgt_tok,
            rect,
            patch_w=int(dmg["patch_w"]),
            patch_h=int(dmg["patch_h"]),
            count=int(dmg["damage_patches"]),
            seed=seed + 999,
        )
        seed_t = torch.zeros(1, channel_n, h, w, device=dev)
        seed_t[:, :token_count] = eval_inp.unsqueeze(0)
        final_x = nca_rollout_eval(rule, seed_t, kx, ky, int(profile["steps"]))

    block = ensure_agent_prism(state)
    block.setdefault("nca", {}).setdefault("models", {})[lid] = str(model_path.resolve())
    state["field_version"] = int(state.get("field_version") or 0) + 1

    return {
        "lattice_id": lid,
        "epochs": ep,
        "best_loss": run.best_loss,
        "model_path": str(model_path),
        "token_count": token_count,
        "eval_max_activation": float(final_x.max().cpu()),
    }
