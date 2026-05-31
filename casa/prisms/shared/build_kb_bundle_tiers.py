#!/usr/bin/env python3
"""Build manifests/kb-bundle-tiers.v0.json from Experiment E (or other) bench report."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    p = argparse.ArgumentParser(description="Generate bundle tier manifest from bench baselines")
    p.add_argument("--bench-root", type=Path, default=Path("lab/exp_e_clusters_v1"))
    p.add_argument("--clusters", type=Path, default=Path("manifests/kb-clusters.v0.json"))
    p.add_argument("--threshold", type=float, default=0.85)
    p.add_argument("--out", type=Path, default=Path("manifests/kb-bundle-tiers.v0.json"))
    args = p.parse_args()

    clusters = _read(args.clusters.resolve())
    bundle_dir = clusters["bundle_dir"]
    rows: list[dict] = []

    for cl in clusters["clusters"]:
        cid = cl["id"]
        for bname in cl["bundles"]:
            bench_path = args.bench_root / cid / f"bench_{Path(bname).stem}.json"
            if not bench_path.is_file():
                continue
            rep = _read(bench_path)
            bc = rep["baseline"]["concepts_f1"]["mean"]
            be = rep["baseline"]["edges_f1"]["mean"]
            bm = bc * 0.6 + be * 0.4
            rows.append(
                {
                    "bundle": bname,
                    "cluster": cid,
                    "tier": "easy" if bm >= args.threshold else "hard",
                    "baseline_mix": bm,
                }
            )

    out = {
        "schema_version": 1,
        "baseline_threshold": args.threshold,
        "tier_policy": {
            "easy": "cluster_dmn_only (Experiment E style, full-field loss)",
            "hard": "cluster_dmn then module_masked finetune (Experiment G phase 2)",
        },
        "source": f"{args.bench_root} baseline_mix @ damage 0.4",
        "bundles": sorted(rows, key=lambda r: (r["cluster"], r["bundle"])),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"written": str(args.out), "count": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
