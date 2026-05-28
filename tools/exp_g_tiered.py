#!/usr/bin/env python3
"""Experiment G: tiered train (easy=cluster only, hard=cluster+module) + bench."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True)


def main() -> None:
    p = argparse.ArgumentParser(description="Experiment G — tiered bundle training")
    p.add_argument("--clusters", type=Path, default=Path("manifests/kb-clusters.v0.json"))
    p.add_argument("--tiers", type=Path, default=Path("manifests/kb-bundle-tiers.v0.json"))
    p.add_argument("--modules", type=Path, default=Path("manifests/kb-modules.v0.json"))
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--phase1-epochs", type=int, default=600)
    p.add_argument("--phase2-epochs", type=int, default=200)
    p.add_argument("--seeds", type=int, default=15)
    p.add_argument("--damage", type=float, default=0.4)
    p.add_argument("--out-root", type=Path, default=Path("examples/exp_g_tiered_v1"))
    p.add_argument("--skip-train", action="store_true")
    args = p.parse_args()

    repo = args.repo_root.resolve()
    tools = repo / "tools"
    spec = _read((repo / args.clusters).resolve())
    tiers_spec = _read((repo / args.tiers).resolve())
    bundle_dir = repo / spec["bundle_dir"]
    out_root = (repo / args.out_root).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    tier_by_bundle = {r["bundle"]: r for r in tiers_spec["bundles"]}
    cluster_reports: list[dict] = []

    for cl in spec["clusters"]:
        cid = cl["id"]
        paths = [bundle_dir / b for b in cl["bundles"] if (bundle_dir / b).is_file()]
        out_dir = out_root / cid
        out_dir.mkdir(parents=True, exist_ok=True)
        model = out_dir / "model.pt"

        if not args.skip_train:
            _run(
                [
                    sys.executable,
                    str(tools / "train_tiered_cluster.py"),
                    "--cluster",
                    cid,
                    "--repo-root",
                    str(repo),
                    "--clusters",
                    str(args.clusters),
                    "--tiers",
                    str(args.tiers),
                    "--modules",
                    str(args.modules),
                    "--phase1-epochs",
                    str(args.phase1_epochs),
                    "--phase2-epochs",
                    str(args.phase2_epochs),
                    "--out-dir",
                    str(out_dir),
                ],
                repo,
            )

        bench_rows: list[dict] = []
        for b in paths:
            bout = out_dir / f"bench_{b.stem}.json"
            _run(
                [
                    sys.executable,
                    str(tools / "bench_dmn_nca_union.py"),
                    "--bundle",
                    str(b),
                    "--model",
                    str(model),
                    "--codec",
                    "v3",
                    "--concept-mode",
                    "section",
                    "--damage",
                    str(args.damage),
                    "--damage-patches",
                    "8",
                    "--seeds",
                    str(args.seeds),
                    "--out",
                    str(bout),
                ],
                repo,
            )
            rep = _read(bout)
            bc = rep["baseline"]["concepts_f1"]["mean"]
            be = rep["baseline"]["edges_f1"]["mean"]
            nc = rep["nca"]["concepts_f1"]["mean"]
            ne = rep["nca"]["edges_f1"]["mean"]
            bm, nm = bc * 0.6 + be * 0.4, nc * 0.6 + ne * 0.4
            tier = tier_by_bundle.get(b.name, {}).get("tier", "unknown")
            bench_rows.append(
                {
                    "bundle": b.name,
                    "tier": tier,
                    "delta_mix": nm - bm,
                    "nca_wins": nm >= bm,
                    "baseline_mix": bm,
                    "nca_mix": nm,
                }
            )

        deltas = [r["delta_mix"] for r in bench_rows]
        cluster_reports.append(
            {
                "cluster": cid,
                "model": str(model.relative_to(repo)),
                "train_mode": "tiered_g_v1",
                "mean_delta_mix": sum(deltas) / len(deltas) if deltas else 0.0,
                "nca_wins": sum(1 for r in bench_rows if r["nca_wins"]),
                "bench_rows": bench_rows,
            }
        )

    report = {
        "schema_version": 1,
        "experiment": "G_tiered_dmn_v1",
        "phase1_epochs": args.phase1_epochs,
        "phase2_epochs": args.phase2_epochs,
        "damage": args.damage,
        "tiers_manifest": str(args.tiers),
        "clusters": cluster_reports,
    }
    (out_root / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
