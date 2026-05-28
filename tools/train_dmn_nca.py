#!/usr/bin/env python3
"""
Train a Neural Cellular Automaton (NCA) to recover a symbolic token grid in the DMN region.

Task:
- Encode bundle -> token grid (codec_grid_v0).
- Apply DMN-only mask (outside region cleared).
- Apply damage inside DMN (drop fraction of cells).
- NCA evolves state for T steps and should reconstruct original grid.

Evaluation:
- Threshold token channels -> recovered grid tokens.
- Decode tokens by voting (codec_grid_v0.decode_grid) -> concept_ids + edges
- Score recovery with PR/F1 (codec_grid_v0.score_recovery)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from codec_grid_v0 import decode_grid, encode_bundle_to_grid, score_recovery  # type: ignore
from layout_apply import _get_region_rect, damage_region, mask_outside_region  # type: ignore


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _threshold_grid_from_state(
    state: torch.Tensor,
    *,
    token_ids: list[str],
    threshold: float = 0.5,
) -> dict:
    """
    state: [1, C, H, W] where first K channels are token logits in [0,1] (we clamp).
    returns grid dict compatible with decode_grid().
    """
    k = len(token_ids)
    x = state[0, :k].detach().cpu().numpy()  # [K,H,W]
    x = np.clip(x, 0.0, 1.0)
    h, w = x.shape[1], x.shape[2]
    cells: list[list[str]] = [[] for _ in range(w * h)]
    for yi in range(h):
        for xi in range(w):
            idx = yi * w + xi
            on = np.where(x[:, yi, xi] >= threshold)[0]
            if on.size:
                cells[idx] = [token_ids[int(j)] for j in on]
    return {"schema_version": 1, "width": w, "height": h, "copies": None, "tokens_count": k, "cells": cells}


def sobel_kernels(device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
    kx = torch.tensor([[-1.0, 0.0, 1.0], [-2.0, 0.0, 2.0], [-1.0, 0.0, 1.0]], device=device)
    ky = kx.T
    return kx.view(1, 1, 3, 3), ky.view(1, 1, 3, 3)


def perceive(x: torch.Tensor, kx: torch.Tensor, ky: torch.Tensor) -> torch.Tensor:
    # x: [B,C,H,W]
    c = x.shape[1]
    kx = kx.repeat(c, 1, 1, 1)
    ky = ky.repeat(c, 1, 1, 1)
    gx = nn.functional.conv2d(x, kx, padding=1, groups=c)
    gy = nn.functional.conv2d(x, ky, padding=1, groups=c)
    return torch.cat([x, gx, gy], dim=1)


class UpdateRule(nn.Module):
    def __init__(self, channel_n: int, hidden: int = 128) -> None:
        super().__init__()
        perception_n = channel_n * 3
        self.fc0 = nn.Conv2d(perception_n, hidden, 1)
        self.fc1 = nn.Conv2d(hidden, channel_n, 1, bias=False)
        nn.init.zeros_(self.fc1.weight)

    def forward(self, perception: torch.Tensor) -> torch.Tensor:
        return self.fc1(torch.relu(self.fc0(perception)))


def nca_rollout(rule: UpdateRule, x: torch.Tensor, kx: torch.Tensor, ky: torch.Tensor, steps: int, fire_rate: float) -> torch.Tensor:
    for _ in range(steps):
        p = perceive(x, kx, ky)
        dx = rule(p)
        if fire_rate < 1.0:
            mask = (torch.rand_like(dx[:, :1]) + fire_rate).floor()
            dx = dx * mask
        x = x + dx
        x = x.clamp(0.0, 1.0)
    return x


@torch.no_grad()
def nca_rollout_eval(rule: UpdateRule, x: torch.Tensor, kx: torch.Tensor, ky: torch.Tensor, steps: int) -> torch.Tensor:
    return nca_rollout(rule, x, kx, ky, steps, fire_rate=1.0)


def _tokens_for_bundle(bundle: dict) -> list[str]:
    claims = bundle.get("claims", [])
    edges = (bundle.get("graph") or {}).get("edges", [])
    concept_ids = sorted({c.get("concept_id") for c in claims if c.get("concept_id")})
    edge_tokens = []
    for e in edges:
        src, rel, dst = e.get("src"), e.get("relation"), e.get("dst")
        if src and rel and dst:
            edge_tokens.append(f"E:{src}|{rel}|{dst}")
    return [f"C:{cid}" for cid in concept_ids] + sorted(edge_tokens)


def _grid_to_tensor(grid: dict, token_ids: list[str], device: torch.device) -> torch.Tensor:
    w, h = int(grid["width"]), int(grid["height"])
    k = len(token_ids)
    token_to_i = {t: i for i, t in enumerate(token_ids)}
    x = torch.zeros(1, k, h, w, device=device)
    for idx, cell in enumerate(grid["cells"]):
        y = idx // w
        xcoord = idx % w
        for t in cell:
            j = token_to_i.get(t)
            if j is not None:
                x[0, j, y, xcoord] = 1.0
    return x


def main() -> None:
    p = argparse.ArgumentParser(description="Train DMN NCA to recover ontology token grid")
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--layout", type=Path, default=Path("design/layout.v0.json"))
    p.add_argument("--region", default="dmn_ontology")
    p.add_argument("--damage", type=float, default=0.25)
    p.add_argument("--damage-seed", type=int, default=42)
    p.add_argument("--copies", type=int, default=7)
    p.add_argument("--steps", type=int, default=32)
    p.add_argument("--epochs", type=int, default=400)
    p.add_argument("--batch-size", type=int, default=4)
    p.add_argument("--hidden", type=int, default=128)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--fire-rate", type=float, default=0.5)
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--min-votes", type=int, default=3)
    p.add_argument("--out-dir", type=Path, default=Path("examples/nca_out"))
    p.add_argument("--save-model", action="store_true", help="Save best model weights to out-dir/model.pt")
    args = p.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    bundle = _read_json(args.bundle)
    layout = _read_json(args.layout)
    rect = _get_region_rect(layout, args.region)

    token_ids = _tokens_for_bundle(bundle)
    k = len(token_ids)
    channel_n = k + 8  # add a few hidden channels

    # Create target grid (full), then DMN-only masked, then damaged input.
    full_grid = encode_bundle_to_grid(bundle, width=64, height=64, copies=args.copies)
    target_grid = mask_outside_region(full_grid, rect)
    damaged_grid = damage_region(target_grid, rect, drop_fraction=args.damage, seed=args.damage_seed)

    target = _grid_to_tensor(target_grid, token_ids, device=device)
    inp = _grid_to_tensor(damaged_grid, token_ids, device=device)

    # initial state: token channels from damaged input, hidden channels zeros
    seed = torch.zeros(1, channel_n, 64, 64, device=device)
    seed[:, :k] = inp

    kx, ky = sobel_kernels(device)
    rule = UpdateRule(channel_n=channel_n, hidden=args.hidden).to(device)
    opt = torch.optim.Adam(rule.parameters(), lr=args.lr)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    best_f1 = -1.0
    best_state: dict | None = None

    for epoch in range(args.epochs):
        # small batch augmentation: vary damage by re-sampling seed damage
        batch = []
        targets = []
        for b in range(args.batch_size):
            g = damage_region(target_grid, rect, drop_fraction=args.damage, seed=args.damage_seed + epoch * 997 + b * 101)
            x_tok = _grid_to_tensor(g, token_ids, device=device)
            x0 = torch.zeros(1, channel_n, 64, 64, device=device)
            x0[:, :k] = x_tok
            batch.append(x0)
            targets.append(target)
        x = torch.cat(batch, dim=0)
        tgt = torch.cat(targets, dim=0)

        x = nca_rollout(rule, x, kx, ky, args.steps, args.fire_rate)
        pred = x[:, :k]

        loss = nn.functional.mse_loss(pred, tgt)
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(rule.parameters(), 1.0)
        opt.step()

        if epoch % 50 == 0 or epoch == args.epochs - 1:
            with torch.no_grad():
                eval_x = nca_rollout_eval(rule, seed.clone(), kx, ky, args.steps)
                grid_eval = _threshold_grid_from_state(eval_x, token_ids=token_ids, threshold=args.threshold)
                decoded = decode_grid(grid_eval, min_votes=args.min_votes)
                score = score_recovery(bundle, decoded)
                f1 = float(score["concepts"]["f1"] * 0.6 + score["edges"]["f1"] * 0.4)
                if f1 > best_f1:
                    best_f1 = f1
                    best_state = {k: v.detach().clone() for k, v in rule.state_dict().items()}
                print(f"epoch {epoch:4d} loss={loss.item():.6f} f1mix={f1:.3f} concepts={score['concepts']['f1']:.3f} edges={score['edges']['f1']:.3f}")

    if best_state is not None:
        rule.load_state_dict(best_state)

    # final artifacts
    with torch.no_grad():
        final_x = nca_rollout_eval(rule, seed.clone(), kx, ky, args.steps)
        grid_final = _threshold_grid_from_state(final_x, token_ids=token_ids, threshold=args.threshold)
        decoded = decode_grid(grid_final, min_votes=args.min_votes)
        score = score_recovery(bundle, decoded)
        out = {
            "schema_version": 1,
            "bundle": str(args.bundle),
            "layout": str(args.layout),
            "region": args.region,
            "damage": args.damage,
            "steps": args.steps,
            "epochs": args.epochs,
            "token_count": k,
            "decoded": decoded,
            "score": score,
        }
        (args.out_dir / "final_grid.json").write_text(json.dumps(grid_final, ensure_ascii=False, indent=2), encoding="utf-8")
        (args.out_dir / "report.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        if args.save_model:
            torch.save(
                {
                    "schema_version": 1,
                    "channel_n": channel_n,
                    "token_ids": token_ids,
                    "hidden": args.hidden,
                    "steps": args.steps,
                    "fire_rate_train": args.fire_rate,
                    "state_dict": rule.state_dict(),
                },
                args.out_dir / "model.pt",
            )
        print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

