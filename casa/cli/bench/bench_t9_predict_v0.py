#!/usr/bin/env python3
"""Bench T9-style prefix predict + critic on L2 lexicon field."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.cli.bench.bench_predict_v0 import run_bench
from casa.prisms.shared.store_boot_v0 import boot_store


def main() -> None:
    p = argparse.ArgumentParser(description="Bench T9 prefix predict v0")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--cues", type=Path, required=True)
    p.add_argument("--boot-ltm-only", action="store_true", default=True)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    cues_raw = json.loads(args.cues.read_text(encoding="utf-8"))
    cues = []
    for item in cues_raw:
        cues.append(
            {
                **item,
                "modality": item.get("modality") or "t9",
            }
        )

    boot = boot_store(args.store_dir, prefer_field_state=not args.boot_ltm_only)
    report = run_bench(boot["state"], cues, bundle=None)
    report["bench"] = "t9_predict_v0"
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    raise SystemExit(0 if report["passed"] == report["total"] else 1)


if __name__ == "__main__":
    main()
