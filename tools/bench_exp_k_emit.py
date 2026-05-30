#!/usr/bin/env python3
"""
Exp K phase 3: emit Program.cs from query, dotnet build/run (stub — implement in phase 3).

K0 uses bench_answer_recall.py instead.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser(description="Exp K emit+build bench (phase 3 stub)")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--query", type=str, default="напиши консольную игру угадай число на C#")
    p.add_argument("--out-dir", type=Path, default=Path("examples/exp_k_guess_number/out_run1"))
    p.add_argument("--build", action="store_true")
    p.add_argument("--run", action="store_true")
    args = p.parse_args()

    out = {
        "schema_version": 1,
        "status": "not_implemented",
        "phase": 3,
        "message": "Use run_exp_k_smoke.ps1 for K0. Implement: CEN emit_code + articulation + dotnet build.",
        "query": args.query,
        "store_dir": str(args.store_dir),
        "out_dir": str(args.out_dir),
        "gold": "examples/exp_k_guess_number/gold/Program.cs",
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    report = args.out_dir / "report_emit.json"
    report.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(2)


if __name__ == "__main__":
    main()
