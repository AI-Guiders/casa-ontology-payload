#!/usr/bin/env python3
"""Train digest+gate per cluster; wrap exp E + layered phases."""

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
    p = argparse.ArgumentParser(description="Train layered digest+gate per cluster")
    p.add_argument("--manifest", type=Path, default=Path("manifests/kb-clusters.v0.json"))
    p.add_argument("--cluster-root", type=Path, default=Path("examples/exp_e_clusters_v1"))
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--digest-epochs", type=int, default=250)
    p.add_argument("--gate-epochs", type=int, default=250)
    args = p.parse_args()

    repo = args.repo_root.resolve()
    tools = repo / "tools"
    spec = _read_json((repo / args.manifest).resolve())
    bundle_dir = repo / spec["bundle_dir"]
    cluster_root = (repo / args.cluster_root).resolve()

    for cl in spec["clusters"]:
        cid = cl["id"]
        dmn = cluster_root / cid / "model.pt"
        if not dmn.is_file():
            print(f"skip {cid}: no {dmn}")
            continue
        paths = [bundle_dir / b for b in cl["bundles"] if (bundle_dir / b).is_file()]
        if not paths:
            continue
        rep_bundle = paths[0]
        digest_out = cluster_root / cid / "digest_model.pt"
        gate_out = cluster_root / cid / "gate_model.pt"

        _run(
            [
                sys.executable,
                str(tools / "train_layer_digest.py"),
                "--bundle",
                str(rep_bundle),
                "--dmn-model",
                str(dmn),
                "--epochs",
                str(args.digest_epochs),
                "--out",
                str(digest_out),
            ],
            repo,
        )
        _run(
            [
                sys.executable,
                str(tools / "train_layer_gate.py"),
                "--bundle",
                str(rep_bundle),
                "--dmn-model",
                str(dmn),
                "--digest-model",
                str(digest_out),
                "--epochs",
                str(args.gate_epochs),
                "--out",
                str(gate_out),
            ],
            repo,
        )
        print(f"cluster {cid}: digest + gate saved")

    print("done")


if __name__ == "__main__":
    main()
