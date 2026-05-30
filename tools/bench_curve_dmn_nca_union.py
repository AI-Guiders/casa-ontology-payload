#!/usr/bin/env python3
"""
Curve benchmark for a union-token NCA model on a specific bundle.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bench_dmn_nca_union import main as _bench_main  # type: ignore
from layout_apply import _get_region_rect  # type: ignore


def _run_one(args_list: list[str]) -> dict:
    import sys
    from contextlib import redirect_stdout
    from io import StringIO

    old_argv = sys.argv
    try:
        sys.argv = ["bench_dmn_nca_union.py", *args_list]
        buf = StringIO()
        with redirect_stdout(buf):
            _bench_main()
        return json.loads(buf.getvalue().strip())
    finally:
        sys.argv = old_argv


def main() -> None:
    p = argparse.ArgumentParser(description="Benchmark curve baseline vs union-token NCA")
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--layout", type=Path, default=Path("design/layout.v0.json"))
    p.add_argument("--region", default="dmn_ontology")
    p.add_argument("--damages", default="0.10,0.20,0.30,0.40,0.50,0.60")
    p.add_argument("--damage-mode", choices=["drop", "patches"], default="patches")
    p.add_argument("--damage-patches", type=int, default=8, help="Used only if --damage-mode=patches and --patches-from-damage is off")
    p.add_argument("--patch-w", type=int, default=10)
    p.add_argument("--patch-h", type=int, default=10)
    p.add_argument("--patches-from-damage", action="store_true", default=True, help="Derive patch count from damage and DMN/patch areas")
    p.add_argument("--seeds", type=int, default=20)
    p.add_argument("--seed0", type=int, default=1)
    p.add_argument("--copies", type=int, default=7)
    p.add_argument("--steps", type=int, default=48)
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--min-votes", type=int, default=3)
    p.add_argument("--codec", choices=["v0", "v1", "v2", "v3"], default="v3")
    p.add_argument("--concept-mode", choices=["independent", "doc", "section", "doc_section"], default="section")
    p.add_argument("--radius", type=int, default=6)
    p.add_argument("--edge-radius", type=int, default=4)
    p.add_argument("--concept-radius", type=int, default=5)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--out", type=Path, default=Path("lab/nca_bench_union_curve.json"))
    args = p.parse_args()

    damages = [float(x.strip()) for x in args.damages.split(",") if x.strip()]
    layout = json.loads(Path(args.layout).read_text(encoding="utf-8"))
    rect = _get_region_rect(layout, args.region)
    region_area = (rect.x1 - rect.x0 + 1) * (rect.y1 - rect.y0 + 1)
    patch_area = max(1, int(args.patch_w) * int(args.patch_h))
    max_patches = max(1, region_area // patch_area)
    rows: list[dict] = []
    for d in damages:
        if args.damage_mode == "patches" and args.patches_from_damage:
            # approximate "fraction of region cleared" -> patch count
            patches = int(round(float(d) * max_patches))
            patches = max(0, min(max_patches, patches))
        else:
            patches = int(args.damage_patches)

        rep = _run_one(
            [
                "--bundle",
                str(args.bundle),
                "--layout",
                str(args.layout),
                "--region",
                args.region,
                "--damage",
                str(d),
                "--damage-mode",
                args.damage_mode,
                "--damage-patches",
                str(patches),
                "--patch-w",
                str(args.patch_w),
                "--patch-h",
                str(args.patch_h),
                "--seeds",
                str(args.seeds),
                "--seed0",
                str(args.seed0),
                "--copies",
                str(args.copies),
                "--codec",
                args.codec,
                "--concept-mode",
                args.concept_mode,
                "--radius",
                str(args.radius),
                "--edge-radius",
                str(args.edge_radius),
                "--concept-radius",
                str(args.concept_radius),
                "--steps",
                str(args.steps),
                "--threshold",
                str(args.threshold),
                "--min-votes",
                str(args.min_votes),
                "--model",
                str(args.model),
                "--out",
                str(args.out.parent / f"_tmp_union_{Path(args.bundle).stem}_damage_{d:.2f}.json"),
            ]
        )
        rows.append({"damage": d, "patches": patches if args.damage_mode == "patches" else None, "baseline": rep["baseline"], "nca": rep["nca"]})

    curve = {
        "schema_version": 1,
        "bundle": str(args.bundle),
        "layout": str(args.layout),
        "region": args.region,
        "seeds": {"count": args.seeds, "seed0": args.seed0},
        "model": str(args.model),
        "codec": args.codec,
        "concept_mode": args.concept_mode if args.codec == "v3" else None,
        "damage_mode": args.damage_mode,
        "damage_patches": args.damage_patches,
        "patches_from_damage": args.patches_from_damage,
        "patch_w": args.patch_w,
        "patch_h": args.patch_h,
        "region_area": region_area,
        "patch_area": patch_area,
        "max_patches": max_patches,
        "radius": args.radius,
        "edge_radius": args.edge_radius,
        "concept_radius": args.concept_radius if args.codec == "v3" else None,
        "rows": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(curve, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(curve, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

