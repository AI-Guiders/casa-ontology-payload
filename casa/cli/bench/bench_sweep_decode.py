#!/usr/bin/env python3
"""Sweep threshold and min_votes for union NCA decode on one bundle."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

import torch

from casa.cli.bench.bench_dmn_nca_union import (
    _grid_to_union_tensor,
    _read_json,
    _threshold_grid_from_union_state,
    _tokens_for_bundle,
)
from casa.prisms.shared.codec_grid import decode_grid, score_recovery
from casa.prisms.shared.layout_apply import _get_region_rect, damage_region_patches, mask_outside_region
from casa.cli.train_dmn_nca import UpdateRule, nca_rollout_eval, sobel_kernels


def main() -> None:
    p = argparse.ArgumentParser(description="Sweep decode threshold / min_votes")
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--layout", type=Path, default=Path("design/layout.json"))
    p.add_argument("--region", default="dmn_ontology")
    p.add_argument("--damage", type=float, default=0.4)
    p.add_argument("--damage-patches", type=int, default=8)
    p.add_argument("--patch-w", type=int, default=10)
    p.add_argument("--patch-h", type=int, default=10)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--codec", choices=["v2", "v3"], default="v3")
    p.add_argument("--concept-mode", default="section")
    p.add_argument("--steps", type=int, default=48)
    p.add_argument("--thresholds", default="0.35,0.40,0.45,0.50,0.55,0.60")
    p.add_argument("--min-votes", default="2,3,4,5")
    p.add_argument("--out", type=Path, default=Path("lab/decode_sweep_v3_section.json"))
    args = p.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    bundle = _read_json(args.bundle)
    layout = _read_json(args.layout)
    rect = _get_region_rect(layout, args.region)

    if args.codec == "v3":
        from casa.prisms.shared.codec_grid_v3 import encode_bundle_to_grid as enc, tokens_for_bundle as tok

        full = enc(bundle, width=64, height=64, copies=7, concept_mode=args.concept_mode)
        bundle_tokens = set(tok(bundle, concept_mode=args.concept_mode))
    else:
        from casa.prisms.shared.codec_grid_v2 import encode_bundle_to_grid as enc

        full = enc(bundle, width=64, height=64, copies=7)
        bundle_tokens = set(_tokens_for_bundle(bundle))

    target = mask_outside_region(full, rect)
    damaged = damage_region_patches(
        target, rect, patch_w=args.patch_w, patch_h=args.patch_h, count=args.damage_patches, seed=args.seed
    )

    ckpt = torch.load(args.model, map_location="cpu")
    token_ids = list(ckpt["token_ids"])
    token_to_i = {t: i for i, t in enumerate(token_ids)}
    token_count = len(token_ids)
    missing = sorted([t for t in bundle_tokens if t not in token_to_i])
    if missing:
        raise SystemExit(f"model missing tokens: {missing[:5]}")

    rule = UpdateRule(channel_n=int(ckpt["channel_n"]), hidden=int(ckpt["hidden"])).to(device)
    rule.load_state_dict(ckpt["state_dict"])
    rule.eval()
    kx, ky = sobel_kernels(device)
    inp = _grid_to_union_tensor(damaged, token_to_i, device=device)
    x0 = torch.zeros(1, int(ckpt["channel_n"]), 64, 64, device=device)
    x0[:, :token_count] = inp
    with torch.no_grad():
        xT = nca_rollout_eval(rule, x0, kx, ky, steps=args.steps)

    thresholds = [float(x.strip()) for x in args.thresholds.split(",") if x.strip()]
    votes_list = [int(x.strip()) for x in args.min_votes.split(",") if x.strip()]
    rows: list[dict] = []
    best = {"mix_f1": -1.0}
    for th in thresholds:
        grid_logits = _threshold_grid_from_union_state(xT, token_ids=token_ids, threshold=th)
        for mv in votes_list:
            decoded = decode_grid(grid_logits, min_votes=mv)
            score = score_recovery(bundle, decoded)
            mix = float(score["concepts"]["f1"] * 0.6 + score["edges"]["f1"] * 0.4)
            row = {
                "threshold": th,
                "min_votes": mv,
                "concepts_f1": score["concepts"]["f1"],
                "edges_f1": score["edges"]["f1"],
                "mix_f1": mix,
            }
            rows.append(row)
            if mix > best["mix_f1"]:
                best = {**row, "mix_f1": mix}

    out = {
        "schema_version": 1,
        "bundle": str(args.bundle),
        "model": str(args.model),
        "codec": args.codec,
        "concept_mode": args.concept_mode if args.codec == "v3" else None,
        "damage": args.damage,
        "damage_patches": args.damage_patches,
        "seed": args.seed,
        "best": best,
        "rows": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
