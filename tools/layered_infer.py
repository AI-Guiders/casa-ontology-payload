#!/usr/bin/env python3
"""Run layered piston pipeline: encode -> damage -> z=repair -> z=digest -> z=gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

from bench_dmn_nca_union import _threshold_grid_from_union_state  # type: ignore
from canonical import CANONICAL_CONCEPT_MODE, CANONICAL_MIN_VOTES, CANONICAL_THRESHOLD  # type: ignore
from codec_grid_v0 import decode_grid, score_recovery  # type: ignore
from layout_apply import _get_region_rect, damage_region_patches, mask_outside_region  # type: ignore
from layered_nca_core import (  # type: ignore
    LayeredChannelLayout,
    grid_to_layered_state,
    load_dmn_rule,
    run_piston_pipeline,
)
from train_dmn_nca import UpdateRule  # type: ignore


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    p = argparse.ArgumentParser(description="Layered CA piston infer")
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--dmn-model", type=Path, required=True)
    p.add_argument("--digest-model", type=Path, default=None)
    p.add_argument("--layout", type=Path, default=Path("design/layout.v0.json"))
    p.add_argument("--damage-patches", type=int, default=8)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--dmn-steps", type=int, default=48)
    p.add_argument("--digest-steps", type=int, default=16)
    p.add_argument("--out", type=Path, default=Path("examples/layered_out/infer_report.json"))
    args = p.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    bundle = _read_json(args.bundle)
    layout_json = _read_json(args.layout)

    from codec_grid_v3 import encode_bundle_to_grid, tokens_for_bundle  # type: ignore

    full = encode_bundle_to_grid(bundle, width=64, height=64, copies=7, concept_mode=CANONICAL_CONCEPT_MODE)
    dmn_rect = _get_region_rect(layout_json, "dmn_ontology")
    target_grid = mask_outside_region(full, dmn_rect)
    damaged = damage_region_patches(
        target_grid, dmn_rect, patch_w=10, patch_h=10, count=args.damage_patches, seed=args.seed
    )

    token_ids = sorted(tokens_for_bundle(bundle, concept_mode=CANONICAL_CONCEPT_MODE))
    field_layout = LayeredChannelLayout(k_tokens=len(token_ids))
    dmn_rule, ckpt_ids, dm_c = load_dmn_rule(args.dmn_model, field_layout, device)
    if list(ckpt_ids) != token_ids:
        raise SystemExit("dmn model token_ids mismatch bundle")

    digest_rule = None
    if args.digest_model and args.digest_model.is_file():
        dck = torch.load(args.digest_model, map_location="cpu")
        digest_rule = UpdateRule(channel_n=int(dck["channel_n"]), hidden=int(dck["hidden"])).to(device)
        digest_rule.load_state_dict(dck["state_dict"])
        digest_rule.eval()

    x = grid_to_layered_state(damaged, token_ids, field_layout, device)
    x = run_piston_pipeline(
        x,
        field_layout=field_layout,
        layout_json=layout_json,
        dmn_rule=dmn_rule,
        dm_channel_n=dm_c,
        digest_rule=digest_rule,
        dmn_steps=args.dmn_steps,
        digest_steps=args.digest_steps,
        run_gate=True,
    )

    grid_logits = _threshold_grid_from_union_state(x, token_ids=token_ids, threshold=CANONICAL_THRESHOLD)
    decoded = decode_grid(grid_logits, min_votes=CANONICAL_MIN_VOTES)
    score = score_recovery(bundle, decoded)

    digest_vec = x[0, field_layout.digest_slice, :, :].mean(dim=(1, 2)).detach().cpu().tolist()
    gate_vec = x[0, field_layout.gate_slice, :, :].mean(dim=(1, 2)).detach().cpu().tolist()

    report = {
        "schema_version": 1,
        "pipeline": "layered_piston_v0",
        "bundle": str(args.bundle),
        "dmn_model": str(args.dmn_model),
        "digest_model": str(args.digest_model) if args.digest_model else None,
        "damage_patches": args.damage_patches,
        "phases": ["encode", "dmn_repair", "digest" if digest_rule else "digest_skip", "gate"],
        "recovery": score,
        "digest_mean": digest_vec,
        "gate_mean": gate_vec,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
