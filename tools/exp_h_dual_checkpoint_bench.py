#!/usr/bin/env python3
"""
Experiment H: bench with tier-routed checkpoints (easy=phase1, hard=phase2).

Uses existing G train outputs; phase1 fallback from E if model_phase1.pt missing.
"""

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


def _resolve_model(
    cluster_dir: Path,
    tier: str,
    *,
    e_fallback: Path,
) -> Path:
    p1 = cluster_dir / "model_phase1.pt"
    ph = cluster_dir / "model_hard.pt"
    legacy = cluster_dir / "model.pt"
    if tier == "easy":
        if p1.is_file():
            return p1
        e_model = e_fallback / "model.pt"
        if e_model.is_file():
            return e_model
        return legacy
    if ph.is_file():
        return ph
    return legacy


def main() -> None:
    p = argparse.ArgumentParser(description="Experiment H — dual-checkpoint tiered bench")
    p.add_argument("--clusters", type=Path, default=Path("manifests/kb-clusters.v0.json"))
    p.add_argument("--tiers", type=Path, default=Path("manifests/kb-bundle-tiers.v0.json"))
    p.add_argument("--g-root", type=Path, default=Path("examples/exp_g_tiered_v1"))
    p.add_argument("--e-fallback", type=Path, default=Path("examples/exp_e_clusters_v1"))
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--seeds", type=int, default=15)
    p.add_argument("--damage", type=float, default=0.4)
    p.add_argument("--out-root", type=Path, default=Path("examples/exp_h_dual_bench_v1"))
    args = p.parse_args()

    repo = args.repo_root.resolve()
    tools = repo / "tools"
    spec = _read((repo / args.clusters).resolve())
    tiers = _read((repo / args.tiers).resolve())
    tier_by = {(r["cluster"], r["bundle"]): r["tier"] for r in tiers["bundles"]}
    bundle_dir = repo / spec["bundle_dir"]
    out_root = (repo / args.out_root).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    cluster_reports: list[dict] = []
    for cl in spec["clusters"]:
        cid = cl["id"]
        g_dir = (repo / args.g_root / cid).resolve()
        e_dir = (repo / args.e_fallback / cid).resolve()
        out_dir = out_root / cid
        out_dir.mkdir(parents=True, exist_ok=True)
        bench_rows: list[dict] = []

        for bname in cl["bundles"]:
            bpath = bundle_dir / bname
            if not bpath.is_file():
                continue
            tier = tier_by.get((cid, bname), "easy")
            model = _resolve_model(g_dir, tier, e_fallback=e_dir)
            bout = out_dir / f"bench_{bpath.stem}.json"
            _run(
                [
                    sys.executable,
                    str(tools / "bench_dmn_nca_union.py"),
                    "--bundle",
                    str(bpath),
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
            bench_rows.append(
                {
                    "bundle": bname,
                    "tier": tier,
                    "model_used": str(model.relative_to(repo)),
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
                "train_mode": "dual_checkpoint_infer_v1",
                "mean_delta_mix": sum(deltas) / len(deltas) if deltas else 0.0,
                "nca_wins": sum(1 for r in bench_rows if r["nca_wins"]),
                "bench_rows": bench_rows,
            }
        )

    report = {
        "schema_version": 1,
        "experiment": "H_dual_checkpoint_bench_v1",
        "policy": "easy -> model_phase1 (or E fallback); hard -> model_hard",
        "g_root": str(args.g_root),
        "damage": args.damage,
        "clusters": cluster_reports,
    }
    (out_root / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
