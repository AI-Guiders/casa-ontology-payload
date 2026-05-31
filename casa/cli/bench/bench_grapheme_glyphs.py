#!/usr/bin/env python3
"""Bench: cursive grapheme PNG manifest (Script MT / Propisi)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import sys
from pathlib import Path

from casa.prisms.memory.grapheme_ingest import GRAPHEME_CYRL_PREFIX, GRAPHEME_LATN_PREFIX


def run_bench(manifest_path: Path, *, expect_latn: int = 26) -> dict:
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    glyphs = doc.get("glyphs") or []
    root = manifest_path.parent
    latn = [g for g in glyphs if str(g.get("concept_id", "")).startswith(GRAPHEME_LATN_PREFIX)]
    cyrl = [g for g in glyphs if str(g.get("concept_id", "")).startswith(GRAPHEME_CYRL_PREFIX)]
    missing_files = [
        g.get("png")
        for g in glyphs
        if not (root / str(g.get("png") or "")).is_file()
    ]
    latn_ok = len(latn) >= expect_latn
    files_ok = len(missing_files) == 0
    passed = latn_ok and files_ok
    total = 2
    score = int(latn_ok) + int(files_ok)
    return {
        "schema_version": 1,
        "bench": "grapheme_glyphs",
        "passed": score,
        "total": total,
        "all_passed": passed,
        "latn_count": len(latn),
        "cyrl_count": len(cyrl),
        "expect_latn_min": expect_latn,
        "missing_files": missing_files[:8],
        "style": doc.get("style"),
        "sources": doc.get("sources"),
    }


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Bench cursive grapheme PNG manifest")
    p.add_argument(
        "--manifest",
        type=Path,
        default=root / "lab/exp_bilingual/grapheme-glyphs/manifest.v1.json",
    )
    args = p.parse_args()
    if not args.manifest.is_file():
        print(f"ERROR: run grapheme_glyph_export.py first — {args.manifest} missing", file=sys.stderr)
        raise SystemExit(1)
    report = run_bench(args.manifest)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nSUMMARY: {report['passed']}/{report['total']}", file=sys.stderr)
    raise SystemExit(0 if report["all_passed"] else 1)


if __name__ == "__main__":
    main()
