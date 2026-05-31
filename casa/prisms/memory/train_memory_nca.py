#!/usr/bin/env python3
"""Train NCA to recover SSS memory lattice (default L2_word)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from casa.prisms.shared.field_write import load_field_state
from casa.prisms.shared.lattice_names_v1 import require_lattice
from casa.prisms.shared.layout_apply import Rect
from casa.prisms.shared.nca_train_core import NcaTrainerConfig, WindowedTrainConfig, run_nca_training
from casa.prisms.shared.nca_train_defaults import (
    add_windowed_train_args,
    damage_defaults,
    epoch_budget,
    field_edge,
    nca_profile,
)
from casa.prisms.shared.nca_train_util import (
    add_device_args,
    damage_tensor_patches,
    grid_indices,
    resolve_train_device,
    scatter_grid_tensor,
)
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.memory.nca_codec import lattice_as_grid, tokens_from_lattice
from casa.prisms.shared.store_layout import rel_to_repo
from casa.cli.train_dmn_nca import UpdateRule, nca_rollout_eval, sobel_kernels


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _threshold_grid_from_state(state: torch.Tensor, *, token_ids: list[str], threshold: float = 0.5) -> dict:
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


def _lattice_rect(lattice: dict) -> Rect:
    w = int(lattice["width"])
    h = int(lattice["height"])
    return Rect(x0=0, y0=0, x1=w - 1, y1=h - 1)


def main() -> None:
    _sss = nca_profile("sss")
    _dmg = damage_defaults()
    _fe = field_edge("sss_lattice")

    p = argparse.ArgumentParser(description="Train SSS NCA on memory or control lattice")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--lattice-id", default="L2_word")
    p.add_argument(
        "--prism",
        choices=("memory", "control"),
        default="memory",
        help="memory=prism_memory lattices; control=prism_control (lattice_predict, …)",
    )
    p.add_argument("--damage-patches", type=int, default=_dmg["damage_patches"])
    p.add_argument("--patch-w", type=int, default=_dmg["patch_w"])
    p.add_argument("--patch-h", type=int, default=_dmg["patch_h"])
    p.add_argument("--steps", type=int, default=int(_sss["steps"]))
    p.add_argument("--epochs", type=int, default=epoch_budget("sss_monolith"))
    add_device_args(p)
    add_windowed_train_args(p, field_edge=_fe, windowed_default=True)
    p.add_argument("--hidden", type=int, default=int(_sss["hidden"]))
    p.add_argument("--lr", type=float, default=float(_sss["lr"]))
    p.add_argument("--fire-rate", type=float, default=float(_sss["fire_rate"]))
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--out-dir", type=Path, default=Path("lab/nca_out_sss_l2"))
    p.add_argument("--save-model", action="store_true")
    args = p.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    device = resolve_train_device(args.device)

    state = ensure_prisms(load_field_state(args.store_dir / "field_state.json"))
    if args.prism == "control":
        from casa.prisms.control.cylinders import control_lattices

        lattices = control_lattices(state)
    else:
        lattices = memory_lattices(state)
    try:
        lattice_key = require_lattice(args.lattice_id, lattices)
    except KeyError as exc:
        raise SystemExit(str(exc)) from exc
    lattice = lattices[lattice_key]

    grid = lattice_as_grid(lattice)
    token_ids = tokens_from_lattice(lattice)
    if not token_ids:
        raise SystemExit("Lattice has no tokens to train on")

    token_count = len(token_ids)
    channel_n = token_count + 6
    h = int(grid["height"])
    w = int(grid["width"])
    rect = _lattice_rect(lattice)
    token_to_i = {t: i for i, t in enumerate(token_ids)}
    tgt_tok = scatter_grid_tensor(
        grid_indices(grid, token_to_i), token_channels=token_count, h=h, w=w, device=device
    )[0]

    args.out_dir.mkdir(parents=True, exist_ok=True)

    train_cfg = NcaTrainerConfig(
        token_channels=token_count,
        h=h,
        w=w,
        hidden=args.hidden,
        channel_extra=6,
        steps=args.steps,
        epochs=args.epochs,
        lr=args.lr,
        fire_rate=args.fire_rate,
        damage_patches=args.damage_patches,
        patch_w=args.patch_w,
        patch_h=args.patch_h,
        seed=args.seed,
        device=args.device,
        batch_size=args.batch_size,
        amp=args.amp,
    )
    win_cfg = WindowedTrainConfig(
        tile_w=args.tile_w,
        tile_h=args.tile_h,
        stride_x=args.stride_x,
        stride_y=args.stride_y,
        ghost=args.ghost,
        windows_per_batch=args.windows_per_batch,
        max_windows_per_batch=args.max_windows_per_batch,
        edge_weight=args.edge_weight,
    )
    mode = "windowed" if args.windowed else "full"
    run = run_nca_training(
        train_cfg,
        tgt=tgt_tok,
        rect=rect,
        mode=mode,
        windowed=win_cfg,
    )
    best_loss = run.best_loss
    rule = UpdateRule(channel_n=channel_n, hidden=args.hidden).to(device)
    rule.load_state_dict(run.state_dict)
    kx, ky = sobel_kernels(device)

    with torch.no_grad():
        eval_inp = damage_tensor_patches(
            tgt_tok, rect, patch_w=args.patch_w, patch_h=args.patch_h, count=args.damage_patches, seed=args.seed + 999
        )
        seed_t = torch.zeros(1, channel_n, h, w, device=device)
        seed_t[:, :token_count] = eval_inp.unsqueeze(0)
        final_x = nca_rollout_eval(rule, seed_t, kx, ky, args.steps)
        grid_final = _threshold_grid_from_state(final_x, token_ids=token_ids, threshold=args.threshold)

    w_before = sum(1 for cell in grid["cells"] for t in cell if t.startswith("W:"))
    w_after = sum(1 for cell in grid_final["cells"] for t in cell if t.startswith("W:"))

    report = {
        "schema_version": 1,
        "lattice_id": lattice_key,
        "store": rel_to_repo(args.store_dir) or args.store_dir.name,
        "token_count": token_count,
        "grid_size": [w, h],
        "epochs": args.epochs,
        "steps": args.steps,
        "train_mode": run.mode,
        "best_loss": best_loss,
        "w_tokens_before_damage_eval": w_before,
        "w_tokens_after_nca_eval": w_after,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "final_grid.json").write_text(json.dumps(grid_final, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.out_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.save_model:
        torch.save(
            {
                "schema_version": 1,
                "kind": "sss_lattice_nca",
                "lattice_id": lattice_key,
                "channel_n": channel_n,
                "token_ids": token_ids,
                "width": w,
                "height": h,
                "hidden": args.hidden,
                "steps": args.steps,
                "fire_rate_train": args.fire_rate,
                "state_dict": rule.state_dict(),
            },
            args.out_dir / "model.pt",
        )

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
