#!/usr/bin/env python3
"""Bench Exp L0 predict loop: schema modality + critic (UC v0.6)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from bench_predict_v0 import run_bench  # type: ignore
from f0_math_ingest_v0 import ingest_math_bundle  # type: ignore
from store_boot_v0 import boot_store  # type: ignore


def main() -> None:
    p = argparse.ArgumentParser(description="Bench F0 schema predict + critic")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--cues", type=Path, required=True)
    p.add_argument("--ingest", action="store_true", help="Ingest bundle onto F0 before bench")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    cues = json.loads(args.cues.read_text(encoding="utf-8"))
    boot = boot_store(args.store_dir, prefer_field_state=False)
    state = boot["state"]
    if args.ingest:
        ingest_math_bundle(state, bundle)

    report = run_bench(state, cues, bundle=bundle)
    report["bench"] = "schema_predict_v0"
    report["boot_source"] = boot.get("source")
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    raise SystemExit(0 if report["passed"] == report["total"] else 1)


if __name__ == "__main__":
    main()
