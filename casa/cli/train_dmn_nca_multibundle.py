#!/usr/bin/env python3
"""
Train a single DMN NCA on a MIX of bundles with a unified token vocabulary.

Goal: learn a more transferable "recovery prior" than per-bundle training.
"""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from codec_grid_v0 import decode_grid, score_recovery  # type: ignore
from layout_apply import _get_region_rect, damage_region, damage_region_patches, mask_outside_region  # type: ignore
from nca_train_util import (  # type: ignore
    add_device_args,
    configure_cuda,
    damage_tensor_patches,
    grid_indices,
    print_train_device,
    resolve_amp,
    resolve_batch_size,
    empty_cuda_cache,
    resolve_train_device,
    scatter_grid_tensor,
)
from train_dmn_nca import UpdateRule, nca_rollout, nca_rollout_eval, sobel_kernels  # type: ignore


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _tokens_for_bundle(bundle: dict) -> list[str]:
    claims = bundle.get("claims", [])
    graph = bundle.get("graph") or {}
    edges = graph.get("edges", [])
    nodes = graph.get("nodes", [])
    concept_ids = sorted({c.get("concept_id") for c in claims if c.get("concept_id")})
    node_ids: set[str] = set()
    for n in nodes or []:
        if isinstance(n, dict) and n.get("id"):
            node_ids.add(str(n["id"]))
    if not node_ids:
        for e in edges:
            src, dst = e.get("src"), e.get("dst")
            if src:
                node_ids.add(str(src))
            if dst:
                node_ids.add(str(dst))
    edge_tokens = []
    for e in edges:
        src, rel, dst = e.get("src"), e.get("relation"), e.get("dst")
        if src and rel and dst:
            edge_tokens.append(f"E:{src}|{rel}|{dst}")
    return [f"C:{cid}" for cid in concept_ids] + [f"N:{nid}" for nid in sorted(node_ids)] + sorted(edge_tokens)


def _grid_to_union_tensor(grid: dict, token_to_i: dict[str, int], device: torch.device) -> torch.Tensor:
    w, h = int(grid["width"]), int(grid["height"])
    token_count = len(token_to_i)
    x = torch.zeros(1, token_count, h, w, device=device)
    for idx, cell in enumerate(grid["cells"]):
        y = idx // w
        xcoord = idx % w
        for t in cell:
            j = token_to_i.get(t)
            if j is not None:
                x[0, j, y, xcoord] = 1.0
    return x


def _threshold_grid_from_union_state(
    state: torch.Tensor,
    *,
    token_ids: list[str],
    threshold: float,
) -> dict:
    # state: [1, C, H, W] - first K channels correspond to token_ids
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
    return {"schema_version": 1, "width": w, "height": h, "copies": None, "tokens_count": token_count, "cells": cells}


@dataclass(frozen=True)
class BundleSpec:
    path: Path
    bundle: dict
    token_set: set[str]


def main() -> None:
    p = argparse.ArgumentParser(description="Train DMN NCA on multiple bundles with unified token space")
    p.add_argument("--bundles", nargs="+", type=Path, required=True, help="List of bundle JSON paths")
    p.add_argument("--layout", type=Path, default=Path("design/layout.v0.json"))
    p.add_argument("--region", default="dmn_ontology")
    p.add_argument("--damage", type=float, default=0.25)
    p.add_argument("--damage-mode", choices=["drop", "patches"], default="patches")
    p.add_argument("--damage-patches", type=int, default=6)
    p.add_argument("--patch-w", type=int, default=8)
    p.add_argument("--patch-h", type=int, default=8)
    p.add_argument("--copies", type=int, default=7)
    p.add_argument("--codec", choices=["v0", "v1", "v2", "v3"], default="v3")
    p.add_argument("--concept-mode", choices=["independent", "doc", "section", "doc_section"], default="section")
    p.add_argument("--radius", type=int, default=6, help="Node/section cluster radius (v1/v2/v3)")
    p.add_argument("--edge-radius", type=int, default=4, help="Edge cluster radius (v2/v3)")
    p.add_argument("--concept-radius", type=int, default=5, help="Concept cluster radius (v3)")
    p.add_argument("--steps", type=int, default=48)
    p.add_argument("--epochs", type=int, default=2000)
    add_device_args(p)
    p.add_argument("--hidden", type=int, default=192)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--fire-rate", type=float, default=0.5)
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--min-votes", type=int, default=3)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--edge-weight", type=float, default=5.0, help="Loss multiplier for edge tokens (E:...)")
    p.add_argument("--out-dir", type=Path, default=Path("lab/nca_out_multibundle"))
    p.add_argument("--save-model", action="store_true")
    args = p.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    device = resolve_train_device(args.device)
    configure_cuda(device)
    batch_size = resolve_batch_size(args.batch_size, device)
    use_amp = resolve_amp(args.amp, device)
    print_train_device(device, batch_size, use_amp)

    layout = _read_json(args.layout)
    rect = _get_region_rect(layout, args.region)

    encode_bundle_to_grid = None
    if args.codec == "v3":
        from codec_grid_v3 import encode_bundle_to_grid as _enc_v3, tokens_for_bundle as _tok_v3  # type: ignore

        def encode_bundle_to_grid(bundle: dict, **kw):  # type: ignore[no-redef]
            return _enc_v3(bundle, concept_mode=args.concept_mode, **kw)

        _tokens_for_bundle_fn = lambda b: _tok_v3(b, concept_mode=args.concept_mode)
    elif args.codec == "v2":
        from codec_grid_v2 import encode_bundle_to_grid  # type: ignore

        _tokens_for_bundle_fn = _tokens_for_bundle
    elif args.codec == "v1":
        from codec_grid_v1 import encode_bundle_to_grid  # type: ignore

        _tokens_for_bundle_fn = _tokens_for_bundle
    else:
        from codec_grid_v0 import encode_bundle_to_grid  # type: ignore

        _tokens_for_bundle_fn = _tokens_for_bundle

    specs: list[BundleSpec] = []
    union_tokens: set[str] = set()
    for bp in args.bundles:
        b = _read_json(bp)
        toks = set(_tokens_for_bundle_fn(b))
        union_tokens |= toks
        specs.append(BundleSpec(path=bp, bundle=b, token_set=toks))

    token_ids = sorted(union_tokens)
    token_to_i = {t: i for i, t in enumerate(token_ids)}
    token_count = len(token_ids)
    channel_n = token_count + 8

    # Per-token weights: emphasize edges so they don't get washed out by concepts.
    token_w = torch.ones(token_count, device=device)
    if args.edge_weight != 1.0:
        for i, t in enumerate(token_ids):
            if t.startswith("E:"):
                token_w[i] = float(args.edge_weight)
    token_w = token_w.view(1, token_count, 1, 1)

    # Precompute per-bundle target tensors on device (DMN-masked grids).
    cached_tgt: dict[Path, torch.Tensor] = {}
    cached_grid: dict[Path, dict] = {}
    h, w = 64, 64
    for s in specs:
        if args.codec == "v3":
            full = encode_bundle_to_grid(
                s.bundle,
                width=w,
                height=h,
                copies=args.copies,
                node_radius=args.radius,
                edge_radius=args.edge_radius,
                concept_radius=args.concept_radius,
            )
        elif args.codec == "v2":
            full = encode_bundle_to_grid(
                s.bundle,
                width=w,
                height=h,
                copies=args.copies,
                node_radius=args.radius,
                edge_radius=args.edge_radius,
            )
        elif args.codec == "v1":
            full = encode_bundle_to_grid(s.bundle, width=w, height=h, copies=args.copies, radius=args.radius)
        else:
            full = encode_bundle_to_grid(s.bundle, width=w, height=h, copies=args.copies)
        target_grid = mask_outside_region(full, rect)
        cached_grid[s.path] = target_grid
        idx = grid_indices(target_grid, token_to_i)
        cached_tgt[s.path] = scatter_grid_tensor(idx, token_channels=token_count, h=h, w=w, device=device)[0]

    kx, ky = sobel_kernels(device)
    rule = UpdateRule(channel_n=channel_n, hidden=args.hidden).to(device)
    opt = torch.optim.Adam(rule.parameters(), lr=args.lr)
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    best_score = -1.0
    best_state: dict | None = None

    for epoch in range(args.epochs):
        batch_tgt: list[torch.Tensor] = []
        batch_inp: list[torch.Tensor] = []

        for b in range(batch_size):
            spec = specs[(epoch * 997 + b * 101) % len(specs)]
            tgt_tok = cached_tgt[spec.path]
            seed = args.seed + epoch * 10007 + b * 97
            if args.damage_mode == "patches":
                inp_tok = damage_tensor_patches(
                    tgt_tok,
                    rect,
                    patch_w=args.patch_w,
                    patch_h=args.patch_h,
                    count=args.damage_patches,
                    seed=seed,
                )
            else:
                target_grid = cached_grid[spec.path]
                dmg = damage_region(target_grid, rect, drop_fraction=args.damage, seed=seed)
                idx = grid_indices(dmg, token_to_i)
                inp_tok = scatter_grid_tensor(idx, token_channels=token_count, h=h, w=w, device=device)[0]
            batch_tgt.append(tgt_tok)
            batch_inp.append(inp_tok)

        tgt = torch.stack(batch_tgt, dim=0)
        inp = torch.stack(batch_inp, dim=0)
        x = torch.zeros(batch_size, channel_n, h, w, device=device)
        x[:, :token_count] = inp

        opt.zero_grad(set_to_none=True)
        with torch.autocast(device_type=device.type, enabled=use_amp):
            x = nca_rollout(rule, x, kx, ky, args.steps, args.fire_rate)
            pred = x[:, :token_count]
            loss = ((pred - tgt).pow(2) * token_w).mean()

        scaler.scale(loss).backward()
        scaler.unscale_(opt)
        torch.nn.utils.clip_grad_norm_(rule.parameters(), 1.0)
        scaler.step(opt)
        scaler.update()
        empty_cuda_cache(device)

        if epoch % 100 == 0 or epoch == args.epochs - 1:
            # quick eval: pick one bundle deterministically
            spec = specs[epoch % len(specs)]
            tgt_tok = cached_tgt[spec.path]
            if args.damage_mode == "patches":
                inp = damage_tensor_patches(
                    tgt_tok,
                    rect,
                    patch_w=args.patch_w,
                    patch_h=args.patch_h,
                    count=args.damage_patches,
                    seed=args.seed + 12345,
                )
            else:
                target_grid = cached_grid[spec.path]
                dmg = damage_region(target_grid, rect, drop_fraction=args.damage, seed=args.seed + 12345)
                idx = grid_indices(dmg, token_to_i)
                inp = scatter_grid_tensor(idx, token_channels=token_count, h=h, w=w, device=device)[0]
            x0 = torch.zeros(1, channel_n, 64, 64, device=device)
            x0[:, :token_count] = inp

            with torch.no_grad():
                xT = nca_rollout_eval(rule, x0, kx, ky, steps=args.steps)
                grid_logits = _threshold_grid_from_union_state(xT, token_ids=token_ids, threshold=args.threshold)
                decoded = decode_grid(grid_logits, min_votes=args.min_votes)
                score = score_recovery(spec.bundle, decoded)
                mix = float(score["concepts"]["f1"] * 0.6 + score["edges"]["f1"] * 0.4)
                if mix > best_score:
                    best_score = mix
                    best_state = {kk: vv.detach().clone() for kk, vv in rule.state_dict().items()}
                print(
                    f"epoch {epoch:4d} loss={loss.item():.6f} eval_bundle={spec.path.name} mix={mix:.3f} "
                    f"c={score['concepts']['f1']:.3f} e={score['edges']['f1']:.3f}"
                )

    if best_state is not None:
        rule.load_state_dict(best_state)

    out_model = args.out_dir / "model.pt"
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
                "bundles": [str(b) for b in args.bundles],
            },
            out_model,
        )

    # Save a final report on each bundle at fixed seed.
    reports = []
    with torch.no_grad():
        for s in specs:
            tgt_tok = cached_tgt[s.path]
            if args.damage_mode == "patches":
                inp = damage_tensor_patches(
                    tgt_tok,
                    rect,
                    patch_w=args.patch_w,
                    patch_h=args.patch_h,
                    count=args.damage_patches,
                    seed=args.seed + 999,
                )
            else:
                target_grid = cached_grid[s.path]
                dmg = damage_region(target_grid, rect, drop_fraction=args.damage, seed=args.seed + 999)
                idx = grid_indices(dmg, token_to_i)
                inp = scatter_grid_tensor(idx, token_channels=token_count, h=h, w=w, device=device)[0]
            x0 = torch.zeros(1, channel_n, 64, 64, device=device)
            x0[:, :token_count] = inp
            xT = nca_rollout_eval(rule, x0, kx, ky, steps=args.steps)
            grid_logits = _threshold_grid_from_union_state(xT, token_ids=token_ids, threshold=args.threshold)
            decoded = decode_grid(grid_logits, min_votes=args.min_votes)
            score = score_recovery(s.bundle, decoded)
            reports.append({"bundle": str(s.path), "score": score})

    out = {
        "schema_version": 1,
        "layout": str(args.layout),
        "region": args.region,
        "damage": args.damage,
        "damage_mode": args.damage_mode,
        "damage_patches": args.damage_patches,
        "patch_w": args.patch_w,
        "patch_h": args.patch_h,
        "steps": args.steps,
        "epochs": args.epochs,
        "edge_weight": args.edge_weight,
        "codec": args.codec,
        "concept_mode": args.concept_mode if args.codec == "v3" else None,
        "token_count_union": token_count,
        "bundles": [str(b) for b in args.bundles],
        "model": str(out_model) if args.save_model else None,
        "reports": reports,
    }
    (args.out_dir / "report.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

