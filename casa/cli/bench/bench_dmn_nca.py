#!/usr/bin/env python3
"""
Benchmark DMN recovery:
- Baseline: damage -> decode
- NCA: damage -> NCA rollout -> decode

Aggregates metrics across seeds (mean/std).
"""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from casa.prisms.shared.codec_grid_v0 import decode_grid, encode_bundle_to_grid, score_recovery
from casa.prisms.shared.layout_apply import _get_region_rect, damage_region, mask_outside_region
from casa.cli.train_dmn_nca import UpdateRule, nca_rollout_eval, sobel_kernels


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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
    token_count = len(token_ids)
    token_to_i = {t: i for i, t in enumerate(token_ids)}
    x = torch.zeros(1, token_count, h, w, device=device)
    for idx, cell in enumerate(grid["cells"]):
        y = idx // w
        xcoord = idx % w
        for t in cell:
            j = token_to_i.get(t)
            if j is not None:
                x[0, j, y, xcoord] = 1.0
    return x


def _threshold_grid_from_logits(
    logits: torch.Tensor,
    *,
    token_ids: list[str],
    threshold: float,
) -> dict:
    token_count = len(token_ids)
    x = logits[0, :token_count].detach().cpu().numpy()
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


def _mean_std(xs: list[float]) -> dict:
    arr = np.array(xs, dtype=np.float64)
    return {"mean": float(arr.mean()), "std": float(arr.std(ddof=1)) if len(xs) > 1 else 0.0}


def main() -> None:
    p = argparse.ArgumentParser(description="Benchmark baseline vs NCA for DMN recovery")
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--layout", type=Path, default=Path("design/layout.v0.json"))
    p.add_argument("--region", default="dmn_ontology")
    p.add_argument("--damage", type=float, default=0.25)
    p.add_argument("--copies", type=int, default=7)
    p.add_argument("--seeds", type=int, default=20)
    p.add_argument("--seed0", type=int, default=1)
    p.add_argument("--min-votes", type=int, default=3)
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--steps", type=int, default=48)
    p.add_argument("--model", type=Path, required=True, help="Path to model.pt saved by train_dmn_nca.py --save-model")
    p.add_argument("--out", type=Path, default=Path("lab/nca_bench_report.json"))
    args = p.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    bundle = _read_json(args.bundle)
    layout = _read_json(args.layout)
    rect = _get_region_rect(layout, args.region)

    token_ids = _tokens_for_bundle(bundle)
    token_count = len(token_ids)

    full_grid = encode_bundle_to_grid(bundle, width=64, height=64, copies=args.copies)
    target_grid = mask_outside_region(full_grid, rect)

    ckpt = torch.load(args.model, map_location="cpu")
    channel_n = int(ckpt["channel_n"])
    if list(ckpt["token_ids"]) != token_ids:
        raise SystemExit("token_ids mismatch: model was trained on different bundle/tokenization")

    rule = UpdateRule(channel_n=channel_n, hidden=int(ckpt["hidden"])).to(device)
    rule.load_state_dict(ckpt["state_dict"])
    rule.eval()
    kx, ky = sobel_kernels(device)

    base_concepts_f1: list[float] = []
    base_edges_f1: list[float] = []
    nca_concepts_f1: list[float] = []
    nca_edges_f1: list[float] = []

    for i in range(args.seeds):
        seed = args.seed0 + i
        damaged_grid = damage_region(target_grid, rect, drop_fraction=args.damage, seed=seed)

        # baseline
        decoded_base = decode_grid(damaged_grid, min_votes=args.min_votes)
        score_base = score_recovery(bundle, decoded_base)
        base_concepts_f1.append(float(score_base["concepts"]["f1"]))
        base_edges_f1.append(float(score_base["edges"]["f1"]))

        # nca
        inp = _grid_to_tensor(damaged_grid, token_ids, device=device)
        x0 = torch.zeros(1, channel_n, 64, 64, device=device)
        x0[:, :token_count] = inp
        xT = nca_rollout_eval(rule, x0, kx, ky, steps=args.steps)
        grid_logits = _threshold_grid_from_logits(xT, token_ids=token_ids, threshold=args.threshold)
        decoded_nca = decode_grid(grid_logits, min_votes=args.min_votes)
        score_nca = score_recovery(bundle, decoded_nca)
        nca_concepts_f1.append(float(score_nca["concepts"]["f1"]))
        nca_edges_f1.append(float(score_nca["edges"]["f1"]))

    report = {
        "schema_version": 1,
        "bundle": str(args.bundle),
        "layout": str(args.layout),
        "region": args.region,
        "damage": args.damage,
        "seeds": {"count": args.seeds, "seed0": args.seed0},
        "baseline": {
            "concepts_f1": _mean_std(base_concepts_f1),
            "edges_f1": _mean_std(base_edges_f1),
        },
        "nca": {
            "model": str(args.model),
            "steps": args.steps,
            "threshold": args.threshold,
            "min_votes": args.min_votes,
            "concepts_f1": _mean_std(nca_concepts_f1),
            "edges_f1": _mean_std(nca_edges_f1),
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

