#!/usr/bin/env python3
"""Experiment C: goal-3 repair grid over patch counts and seeds."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser(description="Experiment C — goal-3 repair grid")
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--bundle", type=Path, default=Path("lab/ca-substrate-agent.bundle.v1.json"))
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--patch-counts", default="6,8,10,12")
    p.add_argument("--seeds", default="1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20")
    p.add_argument("--patch-w", type=int, default=10)
    p.add_argument("--patch-h", type=int, default=10)
    p.add_argument("--out-dir", type=Path, default=Path("lab/exp_c_goal3_grid_v1"))
    args = p.parse_args()

    repo = args.repo_root.resolve()
    tools = repo / "tools"
    model = (repo / args.model).resolve() if not Path(args.model).is_absolute() else Path(args.model)
    bundle = (repo / args.bundle).resolve()
    out_dir = (repo / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    patch_counts = [int(x.strip()) for x in args.patch_counts.split(",") if x.strip()]
    seeds = [int(x.strip()) for x in args.seeds.split(",") if x.strip()]

    rows: list[dict] = []
    for patches in patch_counts:
        for seed in seeds:
            out_json = out_dir / f"p{patches}_s{seed}.json"
            subprocess.run(
                [
                    sys.executable,
                    str(tools / "demo_goal3_repair.py"),
                    "--bundle",
                    str(bundle),
                    "--model",
                    str(model),
                    "--damage-patches",
                    str(patches),
                    "--seed",
                    str(seed),
                    "--patch-w",
                    str(args.patch_w),
                    "--patch-h",
                    str(args.patch_h),
                    "--out",
                    str(out_json),
                ],
                cwd=str(repo),
                check=True,
            )
            d = json.loads(out_json.read_text(encoding="utf-8"))
            dv = d["delta"]["repair_vs_error"]
            win = float(dv["concepts_f1"]) > 0 or float(dv["edges_f1"]) > 0
            rows.append(
                {
                    "patches": patches,
                    "seed": seed,
                    "repair_vs_error": dv,
                    "win": win,
                    "after_error": {
                        "c": d["scores"]["after_agent_error"]["concepts"]["f1"],
                        "e": d["scores"]["after_agent_error"]["edges"]["f1"],
                    },
                    "after_repair": {
                        "c": d["scores"]["after_nca_repair"]["concepts"]["f1"],
                        "e": d["scores"]["after_nca_repair"]["edges"]["f1"],
                    },
                }
            )

    wins = [r for r in rows if r["win"]]
    by_patches: dict[int, list] = {}
    for r in rows:
        by_patches.setdefault(r["patches"], []).append(r)

    patch_summary = []
    for pcount, grp in sorted(by_patches.items()):
        patch_summary.append(
            {
                "patches": pcount,
                "runs": len(grp),
                "win_rate": sum(1 for x in grp if x["win"]) / len(grp),
                "mean_delta_c": sum(x["repair_vs_error"]["concepts_f1"] for x in grp) / len(grp),
                "mean_delta_e": sum(x["repair_vs_error"]["edges_f1"] for x in grp) / len(grp),
            }
        )

    report = {
        "schema_version": 1,
        "experiment": "C_goal3_grid_v1",
        "bundle": str(bundle.relative_to(repo)),
        "model": str(model.relative_to(repo)),
        "total_runs": len(rows),
        "win_count": len(wins),
        "win_rate": len(wins) / len(rows) if rows else 0.0,
        "success_gate_50pct": len(wins) / len(rows) >= 0.5 if rows else False,
        "patch_summary": patch_summary,
        "rows": rows,
    }
    (out_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
