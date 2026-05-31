#!/usr/bin/env python3
"""
Run benchmark across multiple damage levels and save a single curve report.
"""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from bench_dmn_nca import main as _bench_main  # type: ignore


def _run_one(args_list: list[str]) -> dict:
    # Reuse bench_dmn_nca as a subprocess-like call by re-parsing via its CLI.
    # Simpler/portable: just call python bench_dmn_nca.py in shell, but here we keep it in-process.
    import sys
    from io import StringIO
    from contextlib import redirect_stdout

    old_argv = sys.argv
    try:
        sys.argv = ["bench_dmn_nca.py", *args_list]
        buf = StringIO()
        with redirect_stdout(buf):
            _bench_main()
        # last printed JSON is the report
        text = buf.getvalue().strip()
        return json.loads(text)
    finally:
        sys.argv = old_argv


def main() -> None:
    p = argparse.ArgumentParser(description="Benchmark baseline vs NCA across damage levels")
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--layout", type=Path, default=Path("design/layout.v0.json"))
    p.add_argument("--region", default="dmn_ontology")
    p.add_argument("--damages", default="0.10,0.20,0.30,0.40,0.50,0.60")
    p.add_argument("--seeds", type=int, default=20)
    p.add_argument("--seed0", type=int, default=1)
    p.add_argument("--copies", type=int, default=7)
    p.add_argument("--steps", type=int, default=48)
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--min-votes", type=int, default=3)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--out", type=Path, default=Path("lab/nca_bench_curve.json"))
    args = p.parse_args()

    damages = [float(x.strip()) for x in args.damages.split(",") if x.strip()]
    rows: list[dict] = []
    for d in damages:
        rep = _run_one(
            [
                "--bundle",
                str(args.bundle),
                "--layout",
                str(args.layout),
                "--region",
                args.region,
                "--damage",
                str(d),
                "--seeds",
                str(args.seeds),
                "--seed0",
                str(args.seed0),
                "--copies",
                str(args.copies),
                "--steps",
                str(args.steps),
                "--threshold",
                str(args.threshold),
                "--min-votes",
                str(args.min_votes),
                "--model",
                str(args.model),
                "--out",
                str(args.out.parent / f"_tmp_damage_{d:.2f}.json"),
            ]
        )
        rows.append(
            {
                "damage": d,
                "baseline": rep["baseline"],
                "nca": rep["nca"],
            }
        )

    curve = {
        "schema_version": 1,
        "bundle": str(args.bundle),
        "layout": str(args.layout),
        "region": args.region,
        "seeds": {"count": args.seeds, "seed0": args.seed0},
        "model": str(args.model),
        "rows": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(curve, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(curve, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

