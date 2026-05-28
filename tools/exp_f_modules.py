#!/usr/bin/env python3
"""Experiment F: per-cluster module-aware DMN train + bench (vs E cluster baseline)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True)


def main() -> None:
    p = argparse.ArgumentParser(description="Experiment F — module-masked cluster DMN")
    p.add_argument("--clusters", type=Path, default=Path("manifests/kb-clusters.v0.json"))
    p.add_argument("--modules", type=Path, default=Path("manifests/kb-modules.v0.json"))
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--epochs", type=int, default=600)
    p.add_argument("--seeds", type=int, default=15)
    p.add_argument("--damage", type=float, default=0.4)
    p.add_argument("--out-root", type=Path, default=Path("examples/exp_f_modules_v1"))
    p.add_argument("--skip-train", action="store_true")
    args = p.parse_args()

    repo = args.repo_root.resolve()
    tools = repo / "tools"
    spec = _read_json((repo / args.clusters).resolve())
    bundle_dir = repo / spec["bundle_dir"]
    out_root = (repo / args.out_root).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    cluster_reports: list[dict] = []
    for cl in spec["clusters"]:
        cid = cl["id"]
        paths = [bundle_dir / b for b in cl["bundles"]]
        paths = [p for p in paths if p.is_file()]
        out_dir = out_root / cid
        out_dir.mkdir(parents=True, exist_ok=True)
        model = out_dir / "model.pt"

        if not args.skip_train:
            _run(
                [
                    sys.executable,
                    str(tools / "train_module_nca.py"),
                    "--cluster",
                    cid,
                    "--modules",
                    str(args.modules),
                    "--clusters",
                    str(args.clusters),
                    "--repo-root",
                    str(repo),
                    "--epochs",
                    str(args.epochs),
                    "--save-model",
                    "--out-dir",
                    str(out_dir),
                    "--seed",
                    "100",
                ],
                repo,
            )

        mods = [m for m in _read_json((repo / args.modules).resolve())["modules"] if m["cluster"] == cid]
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
            rep = _read_json(bout)
            bc = rep["baseline"]["concepts_f1"]["mean"]
            be = rep["baseline"]["edges_f1"]["mean"]
            nc = rep["nca"]["concepts_f1"]["mean"]
            ne = rep["nca"]["edges_f1"]["mean"]
            bm, nm = bc * 0.6 + be * 0.4, nc * 0.6 + ne * 0.4
            bench_rows.append(
                {
                    "bundle": b.name,
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
                "train_mode": "module_masked_v0",
                "module_count": len(mods),
                "bundles": [b.name for b in paths],
                "mean_delta_mix": sum(deltas) / len(deltas) if deltas else 0.0,
                "nca_wins": sum(1 for r in bench_rows if r["nca_wins"]),
                "bench_rows": bench_rows,
            }
        )

    report = {
        "schema_version": 1,
        "experiment": "F_module_dmn_v1",
        "epochs": args.epochs,
        "damage": args.damage,
        "modules_manifest": str(args.modules),
        "clusters": cluster_reports,
    }
    (out_root / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
