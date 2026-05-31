#!/usr/bin/env python3
"""Tiered cluster train: phase1 cluster DMN (E), phase2 module finetune (hard only)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

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
    p = argparse.ArgumentParser(description="Tiered train for one cluster")
    p.add_argument("--cluster", required=True)
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--clusters", type=Path, default=Path("manifests/kb-clusters.json"))
    p.add_argument("--tiers", type=Path, default=Path("manifests/kb-bundle-tiers.json"))
    p.add_argument("--modules", type=Path, default=Path("manifests/kb-modules.json"))
    p.add_argument("--phase1-epochs", type=int, default=600)
    p.add_argument("--phase2-epochs", type=int, default=200)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--skip-phase1", action="store_true")
    p.add_argument("--skip-phase2", action="store_true")
    args = p.parse_args()

    repo = args.repo_root.resolve()
    tools = repo / "tools"
    spec = _read((repo / args.clusters).resolve())
    tiers = _read((repo / args.tiers).resolve())
    bundle_dir = repo / spec["bundle_dir"]

    cl = next(c for c in spec["clusters"] if c["id"] == args.cluster)
    paths = [bundle_dir / b for b in cl["bundles"] if (bundle_dir / b).is_file()]
    extra = [repo / b for b in spec.get("reference_bundles", []) if (repo / b).is_file()]
    train_paths = sorted(set(paths + extra), key=lambda x: x.name)

    hard_in_cluster = {
        r["bundle"]
        for r in tiers["bundles"]
        if r["cluster"] == args.cluster and r["tier"] == "hard"
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    model = args.out_dir / "model.pt"
    model_phase1 = args.out_dir / "model_phase1.pt"
    model_hard = args.out_dir / "model_hard.pt"

    if not args.skip_phase1:
        print(f"[G] {args.cluster} phase1 cluster_dmn epochs={args.phase1_epochs}")
        _run(
            [
                sys.executable,
                str(tools / "train_dmn_nca_multibundle.py"),
                "--bundles",
                *[str(b) for b in train_paths],
                "--codec",
                "v3",
                "--concept-mode",
                "section",
                "--epochs",
                str(args.phase1_epochs),
                "--save-model",
                "--out-dir",
                str(args.out_dir),
                "--seed",
                "100",
            ],
            repo,
        )
        if model.is_file():
            import shutil

            shutil.copy2(model, model_phase1)
            print(f"saved {model_phase1.name}")

    if not args.skip_phase2 and hard_in_cluster:
        print(
            f"[G] {args.cluster} phase2 module finetune epochs={args.phase2_epochs} "
            f"hard={sorted(hard_in_cluster)}"
        )
        _run(
            [
                sys.executable,
                str(tools / "train_module_nca.py"),
                "--cluster",
                args.cluster,
                "--modules",
                str(args.modules),
                "--clusters",
                str(args.clusters),
                "--tiers",
                str(args.tiers),
                "--hard-only",
                "--init-model",
                str(model),
                "--repo-root",
                str(repo),
                "--epochs",
                str(args.phase2_epochs),
                "--lr",
                "1e-4",
                "--save-model",
                "--out-dir",
                str(args.out_dir),
                "--seed",
                "200",
            ],
            repo,
        )
        if model.is_file():
            import shutil

            shutil.copy2(model, model_hard)
            print(f"saved {model_hard.name}")
    elif not hard_in_cluster:
        print(f"[G] {args.cluster} no hard bundles — skip phase2")
        if model.is_file() and not model_phase1.is_file():
            import shutil

            shutil.copy2(model, model_phase1)

    meta = {
        "schema_version": 1,
        "cluster": args.cluster,
        "train_mode": "tiered_g_v1",
        "phase1_epochs": args.phase1_epochs,
        "phase2_epochs": args.phase2_epochs if hard_in_cluster else 0,
        "hard_bundles": sorted(hard_in_cluster),
        "model": str(model),
        "model_phase1": str(model_phase1) if model_phase1.is_file() else None,
        "model_hard": str(model_hard) if model_hard.is_file() else str(model),
    }
    (args.out_dir / "train_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
