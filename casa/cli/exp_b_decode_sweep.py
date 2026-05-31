#!/usr/bin/env python3
"""Experiment B: decode threshold/min_votes sweep on all reference bundles."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser(description="Experiment B — decode sweep")
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--model", type=Path, required=True)
    p.add_argument(
        "--bundles",
        nargs="*",
        default=None,
        help="Bundle paths; default: 3 examples + all lab/kb/*.bundle.v1.json",
    )
    p.add_argument("--damage", type=float, default=0.4)
    p.add_argument("--out-dir", type=Path, default=Path("lab/exp_b_decode_sweep_v1"))
    args = p.parse_args()

    repo = args.repo_root.resolve()
    tools = repo / "tools"
    model = (repo / args.model).resolve() if not args.model.is_absolute() else args.model

    if args.bundles:
        bundles = [repo / b if not Path(b).is_absolute() else Path(b) for b in args.bundles]
    else:
        bundles = sorted((repo / "lab").glob("*.bundle.v1.json"))
        bundles += sorted((repo / "lab/kb").glob("*.bundle.v1.json"))

    out_dir = (repo / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    per_bundle: list[dict] = []
    global_best_mix = -1.0
    global_best: dict | None = None

    for b in bundles:
        if not b.is_file():
            continue
        sweep_out = out_dir / f"sweep_{b.stem}.json"
        proc = subprocess.run(
            [
                sys.executable,
                str(tools / "bench_sweep_decode.py"),
                "--bundle",
                str(b),
                "--model",
                str(model),
                "--damage",
                str(args.damage),
                "--out",
                str(sweep_out),
            ],
            cwd=str(repo),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()
            per_bundle.append({"bundle": b.name, "skipped": True, "reason": err.splitlines()[-1] if err else "sweep failed"})
            print(f"skip {b.name}: {per_bundle[-1]['reason']}")
            continue
        data = json.loads(sweep_out.read_text(encoding="utf-8"))
        best = data["best"]
        per_bundle.append({"bundle": b.name, "best": best, "path": str(sweep_out.relative_to(repo))})
        if float(best["mix_f1"]) > global_best_mix:
            global_best_mix = float(best["mix_f1"])
            global_best = {"bundle": b.name, **best}

    # Median-ish recommendation across bundles (mode on threshold/votes)
    from collections import Counter

    ths = [round(float(x["best"]["threshold"]), 2) for x in per_bundle]
    mvs = [int(x["best"]["min_votes"]) for x in per_bundle]
    th_mode = Counter(ths).most_common(1)[0][0]
    mv_mode = Counter(mvs).most_common(1)[0][0]

    report = {
        "schema_version": 1,
        "experiment": "B_decode_sweep_v1",
        "model": str(model.relative_to(repo)),
        "damage": args.damage,
        "bundles_tested": len(per_bundle),
        "recommended": {"threshold": th_mode, "min_votes": mv_mode},
        "global_best_row": global_best,
        "per_bundle": per_bundle,
    }
    (out_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
