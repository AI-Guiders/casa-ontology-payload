#!/usr/bin/env python3
"""
Benchmark baseline vs an NCA model trained with a UNION token vocabulary.

This is like bench_dmn_nca.py, but it can evaluate a specific bundle whose tokens are a subset
of the model's union token_ids.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from codec_grid_v0 import decode_grid, score_recovery  # type: ignore
from layout_apply import _get_region_rect, damage_region, damage_region_patches, mask_outside_region  # type: ignore
from canonical import CANONICAL_MIN_VOTES, CANONICAL_THRESHOLD  # type: ignore
from train_dmn_nca import UpdateRule, nca_rollout_eval, sobel_kernels  # type: ignore


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
    k = len(token_to_i)
    x = torch.zeros(1, k, h, w, device=device)
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


def _mean_std(xs: list[float]) -> dict:
    arr = np.array(xs, dtype=np.float64)
    return {"mean": float(arr.mean()), "std": float(arr.std(ddof=1)) if len(xs) > 1 else 0.0}


def main() -> None:
    p = argparse.ArgumentParser(description="Benchmark baseline vs union-token NCA for a specific bundle")
    p.add_argument("--bundle", type=Path, required=True)
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
    p.add_argument("--radius", type=int, default=6)
    p.add_argument("--edge-radius", type=int, default=4)
    p.add_argument("--concept-radius", type=int, default=5)
    p.add_argument("--seeds", type=int, default=20)
    p.add_argument("--seed0", type=int, default=1)
    p.add_argument("--min-votes", type=int, default=CANONICAL_MIN_VOTES)
    p.add_argument("--threshold", type=float, default=CANONICAL_THRESHOLD)
    p.add_argument("--steps", type=int, default=48)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--out", type=Path, default=Path("examples/nca_bench_union.json"))
    args = p.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    bundle = _read_json(args.bundle)
    layout = _read_json(args.layout)
    rect = _get_region_rect(layout, args.region)

    if args.codec == "v3":
        from codec_grid_v3 import encode_bundle_to_grid as _enc_v3, tokens_for_bundle as _tok_v3  # type: ignore

        def encode_bundle_to_grid(bundle: dict, **kw):  # type: ignore[no-redef]
            return _enc_v3(bundle, concept_mode=args.concept_mode, **kw)

        bundle_tokens = set(_tok_v3(bundle, concept_mode=args.concept_mode))
    elif args.codec == "v2":
        from codec_grid_v2 import encode_bundle_to_grid  # type: ignore

        bundle_tokens = set(_tokens_for_bundle(bundle))
    elif args.codec == "v1":
        from codec_grid_v1 import encode_bundle_to_grid  # type: ignore

        bundle_tokens = set(_tokens_for_bundle(bundle))
    else:
        from codec_grid_v0 import encode_bundle_to_grid  # type: ignore

        bundle_tokens = set(_tokens_for_bundle(bundle))

    ckpt = torch.load(args.model, map_location="cpu")
    token_ids = list(ckpt["token_ids"])
    token_to_i = {t: i for i, t in enumerate(token_ids)}
    channel_n = int(ckpt["channel_n"])
    k = len(token_ids)

    missing = sorted([t for t in bundle_tokens if t not in token_to_i])
    if missing:
        raise SystemExit(f"model token_ids missing {len(missing)} bundle tokens, e.g. {missing[:3]}")

    rule = UpdateRule(channel_n=channel_n, hidden=int(ckpt["hidden"])).to(device)
    rule.load_state_dict(ckpt["state_dict"])
    rule.eval()
    kx, ky = sobel_kernels(device)

    if args.codec == "v3":
        full_grid = encode_bundle_to_grid(
            bundle,
            width=64,
            height=64,
            copies=args.copies,
            node_radius=args.radius,
            edge_radius=args.edge_radius,
            concept_radius=args.concept_radius,
        )
    elif args.codec == "v2":
        full_grid = encode_bundle_to_grid(
            bundle,
            width=64,
            height=64,
            copies=args.copies,
            node_radius=args.radius,
            edge_radius=args.edge_radius,
        )
    elif args.codec == "v1":
        full_grid = encode_bundle_to_grid(bundle, width=64, height=64, copies=args.copies, radius=args.radius)
    else:
        full_grid = encode_bundle_to_grid(bundle, width=64, height=64, copies=args.copies)
    target_grid = mask_outside_region(full_grid, rect)

    base_concepts_f1: list[float] = []
    base_edges_f1: list[float] = []
    nca_concepts_f1: list[float] = []
    nca_edges_f1: list[float] = []

    for i in range(args.seeds):
        seed = args.seed0 + i
        if args.damage_mode == "patches":
            damaged_grid = damage_region_patches(
                target_grid,
                rect,
                patch_w=args.patch_w,
                patch_h=args.patch_h,
                count=args.damage_patches,
                seed=seed,
            )
        else:
            damaged_grid = damage_region(target_grid, rect, drop_fraction=args.damage, seed=seed)

        decoded_base = decode_grid(damaged_grid, min_votes=args.min_votes)
        score_base = score_recovery(bundle, decoded_base)
        base_concepts_f1.append(float(score_base["concepts"]["f1"]))
        base_edges_f1.append(float(score_base["edges"]["f1"]))

        inp = _grid_to_union_tensor(damaged_grid, token_to_i, device=device)
        x0 = torch.zeros(1, channel_n, 64, 64, device=device)
        x0[:, :k] = inp
        with torch.no_grad():
            xT = nca_rollout_eval(rule, x0, kx, ky, steps=args.steps)
        grid_logits = _threshold_grid_from_union_state(xT, token_ids=token_ids, threshold=args.threshold)
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
        "codec": args.codec,
        "concept_mode": args.concept_mode if args.codec == "v3" else None,
        "damage_mode": args.damage_mode,
        "damage_patches": args.damage_patches,
        "patch_w": args.patch_w,
        "patch_h": args.patch_h,
        "seeds": {"count": args.seeds, "seed0": args.seed0},
        "baseline": {"concepts_f1": _mean_std(base_concepts_f1), "edges_f1": _mean_std(base_edges_f1)},
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

