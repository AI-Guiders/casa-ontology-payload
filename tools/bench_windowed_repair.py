#!/usr/bin/env python3
"""Compare monolithic vs windowed NCA repair F1 on one bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

from codec_grid_v0 import decode_grid, score_recovery  # type: ignore
from field_planner_v0 import FieldPlannerV0  # type: ignore
from layout_apply import _get_region_rect, mask_outside_region  # type: ignore
from nca_train_util import damage_tensor_patches, grid_indices, scatter_grid_tensor  # type: ignore
from repair_dmn_nca_windowed import repair_field_windowed  # type: ignore
from train_dmn_nca import UpdateRule, nca_rollout_eval, sobel_kernels  # type: ignore
from train_dmn_nca_multibundle import _read_json, _threshold_grid_from_union_state  # type: ignore
from train_dmn_nca_windowed import _tokens_for_bundle  # type: ignore


def _encode_bundle(bundle: dict, args: argparse.Namespace) -> dict:
    w, h = 64, 64
    if args.codec == "v3":
        from codec_grid_v3 import encode_bundle_to_grid  # type: ignore

        return encode_bundle_to_grid(
            bundle,
            width=w,
            height=h,
            copies=args.copies,
            concept_mode=args.concept_mode,
            node_radius=args.radius,
            edge_radius=args.edge_radius,
            concept_radius=args.concept_radius,
        )
    from codec_grid_v0 import encode_bundle_to_grid  # type: ignore

    return encode_bundle_to_grid(bundle, width=w, height=h, copies=args.copies)


def _eval_mode(
    rule: UpdateRule,
    tgt: torch.Tensor,
    planner: FieldPlannerV0,
    *,
    token_channels: int,
    channel_n: int,
    token_ids: list[str],
    bundle: dict,
    args: argparse.Namespace,
    device: torch.device,
    windowed: bool,
) -> dict:
    kx, ky = sobel_kernels(device)
    rect = _get_region_rect(_read_json(args.layout), args.region)
    damaged = damage_tensor_patches(
        tgt,
        rect,
        patch_w=args.patch_w,
        patch_h=args.patch_h,
        count=args.damage_patches,
        seed=args.seed,
    )

    if windowed:
        pred = repair_field_windowed(
            rule,
            tgt,
            planner,
            token_channels=token_channels,
            channel_n=channel_n,
            kx=kx,
            ky=ky,
            steps=args.steps,
            ghost=args.ghost,
            device=device,
            damage_seed=args.seed,
            damage_patches=args.damage_patches,
            patch_w=args.patch_w,
            patch_h=args.patch_h,
        )
    else:
        x0 = torch.zeros(1, channel_n, 64, 64, device=device)
        x0[:, :token_channels] = damaged.unsqueeze(0)
        xT = nca_rollout_eval(rule, x0, kx, ky, steps=args.steps)
        pred = xT[0, :token_channels]

    grid_logits = _threshold_grid_from_union_state(
        pred.unsqueeze(0),
        token_ids=token_ids,
        threshold=args.threshold,
    )
    decoded = decode_grid(grid_logits, min_votes=args.min_votes)
    return score_recovery(bundle, decoded)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--layout", type=Path, default=Path("design/layout.v0.json"))
    p.add_argument("--region", default="dmn_ontology")
    p.add_argument("--codec", default="v3")
    p.add_argument("--concept-mode", default="section")
    p.add_argument("--copies", type=int, default=7)
    p.add_argument("--radius", type=int, default=6)
    p.add_argument("--edge-radius", type=int, default=4)
    p.add_argument("--concept-radius", type=int, default=5)
    p.add_argument("--tile-w", type=int, default=32)
    p.add_argument("--tile-h", type=int, default=32)
    p.add_argument("--stride-x", type=int, default=16)
    p.add_argument("--stride-y", type=int, default=16)
    p.add_argument("--ghost", type=int, default=2)
    p.add_argument("--damage-patches", type=int, default=8)
    p.add_argument("--patch-w", type=int, default=8)
    p.add_argument("--patch-h", type=int, default=8)
    p.add_argument("--steps", type=int, default=48)
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--min-votes", type=int, default=3)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", type=Path, default=Path("examples/exp_j_ru_v1/report_windowed_repair.json"))
    args = p.parse_args()

    ckpt = torch.load(args.model, map_location="cpu", weights_only=False)
    token_ids: list[str] = list(ckpt["token_ids"])
    token_count = len(token_ids)
    channel_n = int(ckpt["channel_n"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    rule = UpdateRule(channel_n=channel_n, hidden=int(ckpt["hidden"])).to(device)
    rule.load_state_dict(ckpt["state_dict"])
    rule.eval()

    bundle = _read_json(args.bundle)
    if args.codec == "v3":
        from codec_grid_v3 import tokens_for_bundle as _tok  # type: ignore

        bundle_tokens = _tok(bundle, concept_mode=args.concept_mode)
    else:
        bundle_tokens = _tokens_for_bundle(bundle)
    token_to_i = {t: i for i, t in enumerate(token_ids)}

    layout = _read_json(args.layout)
    rect = _get_region_rect(layout, args.region)
    full = _encode_bundle(bundle, args)
    grid = mask_outside_region(full, rect)
    idx = grid_indices(grid, token_to_i)
    tgt = scatter_grid_tensor(idx, token_channels=token_count, h=64, w=64, device=device)[0]

    planner = FieldPlannerV0.from_field_tensor(
        tgt,
        rect,
        tile_w=args.tile_w,
        tile_h=args.tile_h,
        stride_x=args.stride_x,
        stride_y=args.stride_y,
    )

    mono = _eval_mode(
        rule, tgt, planner, token_channels=token_count, channel_n=channel_n, token_ids=token_ids, bundle=bundle, args=args, device=device, windowed=False
    )
    win = _eval_mode(
        rule, tgt, planner, token_channels=token_count, channel_n=channel_n, token_ids=token_ids, bundle=bundle, args=args, device=device, windowed=True
    )

    def mix(s: dict) -> float:
        return float(s["concepts"]["f1"] * 0.6 + s["edges"]["f1"] * 0.4)

    out = {
        "schema_version": 1,
        "bundle": str(args.bundle),
        "model": str(args.model),
        "planner": planner.summary(),
        "monolithic": mono,
        "windowed": win,
        "mix_monolithic": mix(mono),
        "mix_windowed": mix(win),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
