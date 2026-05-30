#!/usr/bin/env python3
"""Experiment D: per-doc KB graphs + repeat A (union train, bench, curves)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True)


def main() -> None:
    p = argparse.ArgumentParser(description="Experiment D — per-doc graphs + KB scale")
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--kb-root", type=Path, default=None)
    p.add_argument("--epochs", type=int, default=1200)
    p.add_argument("--seeds", type=int, default=20)
    p.add_argument("--skip-build", action="store_true")
    p.add_argument("--skip-train", action="store_true")
    p.add_argument("--out-dir", type=Path, default=Path("examples/exp_d_kb_perdoc_v1"))
    args = p.parse_args()

    repo = args.repo_root.resolve()
    tools = repo / "tools"
    kb_dir = repo / "examples/kb-perdoc"

    if not args.skip_build:
        cmd = [sys.executable, str(tools / "build_kb_bundles.py"), "--per-doc-graph", "--out-dir", str(kb_dir)]
        if args.kb_root:
            cmd.extend(["--kb-root", str(args.kb_root)])
        _run(cmd, repo)

    exp_out = repo / args.out_dir
    exp_cmd = [
        sys.executable,
        str(tools / "exp_a_kb_scale.py"),
        "--kb-dir",
        str(kb_dir.relative_to(repo)),
        "--epochs",
        str(args.epochs),
        "--seeds",
        str(args.seeds),
        "--out-dir",
        str(exp_out.relative_to(repo)),
        "--extra-bundles",
        "examples/ca-substrate-agent.bundle.v1.json",
        "examples/casa-goals.bundle.v1.json",
        "examples/research-spec.bundle.v1.json",
    ]
    if args.skip_train:
        exp_cmd.append("--skip-train")
    _run(exp_cmd, repo)

    rep = json.loads((exp_out / "report.json").read_text(encoding="utf-8"))
    rep["experiment"] = "D_kb_perdoc_v1"
    rep["kb_build_mode"] = "per_doc"
    (exp_out / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"experiment": "D_kb_perdoc_v1", "summary": rep["summary"]}, indent=2))


if __name__ == "__main__":
    main()
