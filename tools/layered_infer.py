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
    grid_to_layered_state,
    load_dmn_rule,
    run_piston_pipeline,
)
from train_dmn_nca import UpdateRule  # type: ignore


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_cluster(manifest: dict, bundle_path: Path) -> str | None:
    name = bundle_path.name
    for cl in manifest.get("clusters", []):
        if name in cl.get("bundles", []):
            return cl["id"]
    return None


def _load_rule(path: Path, device: torch.device) -> UpdateRule:
    ckpt = torch.load(path, map_location="cpu")
    rule = UpdateRule(channel_n=int(ckpt["channel_n"]), hidden=int(ckpt["hidden"])).to(device)
    rule.load_state_dict(ckpt["state_dict"])
    rule.eval()
    return rule


def main() -> None:
    p = argparse.ArgumentParser(description="Layered CA piston infer")
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--dmn-model", type=Path, default=None)
    p.add_argument("--digest-model", type=Path, default=None)
    p.add_argument("--gate-model", type=Path, default=None)
    p.add_argument("--cluster", default=None, help="Cluster id; auto-resolve checkpoints")
    p.add_argument("--cluster-manifest", type=Path, default=Path("manifests/kb-clusters.v0.json"))
    p.add_argument("--cluster-root", type=Path, default=Path("examples/exp_e_clusters_v1"))
    p.add_argument("--layout", type=Path, default=Path("design/layout.v0.json"))
    p.add_argument("--damage-patches", type=int, default=8)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--dmn-steps", type=int, default=48)
    p.add_argument("--digest-steps", type=int, default=16)
    p.add_argument("--gate-steps", type=int, default=12)
    p.add_argument("--out", type=Path, default=Path("examples/layered_out/infer_report.json"))
    args = p.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    bundle_path = args.bundle.resolve()
    bundle = _read_json(bundle_path)
    layout_json = _read_json(args.layout)

    cluster_id = args.cluster
    if cluster_id is None and args.cluster_manifest.is_file():
        spec = _read_json(args.cluster_manifest.resolve())
        rel = bundle_path.name
        for cl in spec["clusters"]:
            if rel in cl["bundles"] or str(bundle_path).endswith(cl["bundles"][0]):
                for b in cl["bundles"]:
                    if bundle_path.name == b or str(bundle_path).endswith(b.replace("\\", "/")):
                        cluster_id = cl["id"]
                        break
        if cluster_id is None:
            cluster_id = _resolve_cluster(spec, bundle_path)

    cluster_root = args.cluster_root.resolve()
    dmn_path = args.dmn_model
    digest_path = args.digest_model
    gate_path = args.gate_model
    if cluster_id:
        base = cluster_root / cluster_id
        dmn_path = dmn_path or base / "model.pt"
        digest_path = digest_path or base / "digest_model.pt"
        gate_path = gate_path or base / "gate_model.pt"

    if not dmn_path or not Path(dmn_path).is_file():
        raise SystemExit("dmn-model required (or --cluster with trained exp_e_clusters_v1)")

    from codec_grid_v3 import encode_bundle_to_grid  # type: ignore

    full = encode_bundle_to_grid(bundle, width=64, height=64, copies=7, concept_mode=CANONICAL_CONCEPT_MODE)
    dmn_rect = _get_region_rect(layout_json, "dmn_ontology")
    target_grid = mask_outside_region(full, dmn_rect)
    damaged = damage_region_patches(
        target_grid, dmn_rect, patch_w=10, patch_h=10, count=args.damage_patches, seed=args.seed
    )

    dmn_rule, token_ids, dm_c, field_layout = load_dmn_rule(Path(dmn_path), device)

    digest_rule = _load_rule(Path(digest_path), device) if digest_path and Path(digest_path).is_file() else None
    gate_rule = _load_rule(Path(gate_path), device) if gate_path and Path(gate_path).is_file() else None

    x = grid_to_layered_state(damaged, token_ids, field_layout, device)
    x = run_piston_pipeline(
        x,
        field_layout=field_layout,
        layout_json=layout_json,
        dmn_rule=dmn_rule,
        dm_channel_n=dm_c,
        digest_rule=digest_rule,
        gate_rule=gate_rule,
        dmn_steps=args.dmn_steps,
        digest_steps=args.digest_steps,
        gate_steps=args.gate_steps,
        run_gate=True,
    )

    grid_logits = _threshold_grid_from_union_state(x, token_ids=token_ids, threshold=CANONICAL_THRESHOLD)
    decoded = decode_grid(grid_logits, min_votes=CANONICAL_MIN_VOTES)
    score = score_recovery(bundle, decoded)

    report = {
        "schema_version": 1,
        "pipeline": "layered_piston_v1_cluster",
        "bundle": str(bundle_path),
        "cluster": cluster_id,
        "dmn_model": str(dmn_path),
        "digest_model": str(digest_path) if digest_path else None,
        "gate_model": str(gate_path) if gate_path else None,
        "damage_patches": args.damage_patches,
        "recovery": score,
        "digest_mean": x[0, field_layout.digest_slice].mean(dim=(1, 2)).detach().cpu().tolist(),
        "gate_mean": x[0, field_layout.gate_slice].mean(dim=(1, 2)).detach().cpu().tolist(),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
