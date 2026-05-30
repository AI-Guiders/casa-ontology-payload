#!/usr/bin/env python3
"""Compare Experiment E (cluster DMN) vs F (module-masked) reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--e", type=Path, default=Path("examples/exp_e_clusters_v1/report.json"))
    p.add_argument("--f", type=Path, default=Path("examples/exp_f_modules_v2_gpu/report.json"))
    p.add_argument("--out", type=Path, default=Path("examples/exp_compare_ef_v1/report.json"))
    args = p.parse_args()

    e_rep = _read(args.e.resolve())
    f_rep = _read(args.f.resolve())

    e_by = {c["cluster"]: c for c in e_rep["clusters"]}
    f_by = {c["cluster"]: c for c in f_rep["clusters"]}

    rows: list[dict] = []
    for cid in sorted(set(e_by) | set(f_by)):
        e = e_by.get(cid, {})
        f = f_by.get(cid, {})
        rows.append(
            {
                "cluster": cid,
                "E_mean_delta_mix": e.get("mean_delta_mix"),
                "F_mean_delta_mix": f.get("mean_delta_mix"),
                "delta_F_minus_E": (f.get("mean_delta_mix") or 0) - (e.get("mean_delta_mix") or 0),
                "E_wins": e.get("nca_wins"),
                "F_wins": f.get("nca_wins"),
                "F_train_mode": f.get("train_mode"),
            }
        )

    bundle_rows: list[dict] = []
    for cid in sorted(e_by.keys()):
        e_b = {r["bundle"]: r for r in e_by[cid].get("bench_rows", [])}
        f_b = {r["bundle"]: r for r in f_by.get(cid, {}).get("bench_rows", [])}
        for b in sorted(set(e_b) | set(f_b)):
            er, fr = e_b.get(b, {}), f_b.get(b, {})
            bundle_rows.append(
                {
                    "cluster": cid,
                    "bundle": b,
                    "E_delta_mix": er.get("delta_mix"),
                    "F_delta_mix": fr.get("delta_mix"),
                    "F_minus_E": (fr.get("delta_mix") or 0) - (er.get("delta_mix") or 0),
                    "E_win": er.get("nca_wins"),
                    "F_win": fr.get("nca_wins"),
                }
            )

    out = {
        "schema_version": 1,
        "E": str(args.e),
        "F": str(args.f),
        "cluster_summary": rows,
        "per_bundle": bundle_rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
