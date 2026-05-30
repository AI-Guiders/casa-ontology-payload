#!/usr/bin/env python3
"""
train_dmn_stub: region-local "training loop" scaffold (DMN-only) without NCA.

We simulate the DMN module objective:
- Recover the ontology bundle (concept_ids + edges) after damage,
  but only using information inside the DMN region.

In v0, recovery is done by the symbolic codec voting decoder.
This file provides:
- a repeatable experiment runner
- metrics across damage levels

Next step: replace the decoder with a learned/local CA update rule.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from codec_grid_v0 import decode_grid, encode_bundle_to_grid, score_recovery  # type: ignore
from layout_apply import damage_region, mask_outside_region, _get_region_rect  # type: ignore


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def run_once(
    *,
    bundle: dict,
    layout: dict,
    region_id: str,
    width: int,
    height: int,
    copies: int,
    damage: float,
    seed: int,
    min_votes: int,
) -> dict:
    rect = _get_region_rect(layout, region_id)
    grid = encode_bundle_to_grid(bundle, width=width, height=height, copies=copies)
    grid = mask_outside_region(grid, rect)
    if damage > 0:
        grid = damage_region(grid, rect, drop_fraction=damage, seed=seed)
    decoded = decode_grid(grid, min_votes=min_votes)
    score = score_recovery(bundle, decoded)
    return {"damage": damage, "seed": seed, "decoded": decoded, "score": score}


def main() -> None:
    p = argparse.ArgumentParser(description="DMN-only recovery experiment scaffold")
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--layout", type=Path, default=Path("design/layout.v0.json"))
    p.add_argument("--region", default="dmn_ontology")
    p.add_argument("--width", type=int, default=64)
    p.add_argument("--height", type=int, default=64)
    p.add_argument("--copies", type=int, default=7)
    p.add_argument("--min-votes", type=int, default=3)
    p.add_argument("--seeds", type=int, default=5)
    p.add_argument("--damage-levels", default="0.0,0.1,0.2,0.3,0.4")
    p.add_argument("--out", type=Path, default=Path("lab/dmn_stub_report.json"))
    args = p.parse_args()

    bundle = _read_json(args.bundle)
    layout = _read_json(args.layout)
    damage_levels = [float(x.strip()) for x in args.damage_levels.split(",") if x.strip()]

    runs = []
    for d in damage_levels:
        for s in range(args.seeds):
            runs.append(
                run_once(
                    bundle=bundle,
                    layout=layout,
                    region_id=args.region,
                    width=args.width,
                    height=args.height,
                    copies=args.copies,
                    damage=d,
                    seed=s,
                    min_votes=args.min_votes,
                )
            )

    # aggregate mean f1
    def mean(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    summary = {}
    for d in damage_levels:
        subset = [r for r in runs if r["damage"] == d]
        summary[str(d)] = {
            "concepts_f1_mean": mean([r["score"]["concepts"]["f1"] for r in subset]),
            "edges_f1_mean": mean([r["score"]["edges"]["f1"] for r in subset]),
        }

    report = {"schema_version": 1, "bundle": str(args.bundle), "layout": str(args.layout), "region": args.region, "summary": summary, "runs": runs}
    _write_json(args.out, report)
    print(json.dumps({"out": str(args.out), "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

