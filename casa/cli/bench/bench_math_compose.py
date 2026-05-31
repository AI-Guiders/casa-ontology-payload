#!/usr/bin/env python3
"""Bench math compose: entity homogeneity + category lift (livestock)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.prisms.memory.math_compose import run_compose_bench


def main() -> None:
    p = argparse.ArgumentParser(description="Bench quantity compose (entity / category)")
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    report = run_compose_bench(bundle)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    raise SystemExit(0 if report["passed"] == report["total"] else 1)


if __name__ == "__main__":
    main()
