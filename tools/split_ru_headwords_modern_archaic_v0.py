#!/usr/bin/env python3
"""Split RU headwords: modern (DetCorpus) vs archaic (Afan / literary L2 only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lexicon_headwords_v0 import collect_words_from_store, read_headwords, write_headwords  # type: ignore
from field_write import load_field_state  # type: ignore
from sss_cylinders_v0 import ensure_prisms  # type: ignore
from sss_vocab_v0 import norm_word  # type: ignore

REPO = Path(__file__).resolve().parent.parent
DEFAULT_MODERN = REPO / "lab/corpus/ru-general-v0/headwords.v1.txt"
DEFAULT_ARCHAIC_OUT = REPO / "lab/corpus/ru-archaic-v0/headwords.v1.txt"
DEFAULT_REPORT = REPO / "lab/corpus/ru-archaic-v0/split-report.v0.json"


def _load_modern(path: Path) -> set[str]:
    if not path.is_file():
        raise FileNotFoundError(
            f"modern headwords missing: {path}\nRun: python tools/fetch_ru_frequency_headwords_v0.py"
        )
    return {norm_word(w) for w in read_headwords(path)}


def _load_literary(*, store_dir: Path | None, literary_path: Path | None) -> set[str]:
    if literary_path and literary_path.is_file():
        return {norm_word(w) for w in read_headwords(literary_path)}
    if store_dir is None:
        raise ValueError("Provide --literary-store or --literary-headwords")
    fs = store_dir / "field_state.json"
    if not fs.is_file():
        raise FileNotFoundError(f"field_state missing: {fs}")
    state = ensure_prisms(load_field_state(fs))
    votes = collect_words_from_store(state)
    return set(votes.keys())


def split_sets(modern: set[str], literary: set[str]) -> dict[str, set[str]]:
    overlap = modern & literary
    archaic_only = literary - modern
    modern_only = modern - literary
    return {
        "modern": modern,
        "literary": literary,
        "overlap": overlap,
        "archaic_only": archaic_only,
        "modern_only": modern_only,
    }


def build_report(sets: dict[str, set[str]], *, samples: int = 24) -> dict[str, Any]:
    arch = sorted(sets["archaic_only"])
    ov = sorted(sets["overlap"])
    mod = sorted(sets["modern_only"])
    pick = lambda xs: xs[:samples] if len(xs) <= samples else xs[: samples // 2] + xs[-samples // 2 :]

    return {
        "schema_version": 1,
        "kind": "ru_modern_archaic_split_v0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "modern_source": len(sets["modern"]),
            "literary_source": len(sets["literary"]),
            "overlap": len(sets["overlap"]),
            "archaic_only": len(sets["archaic_only"]),
            "modern_only": len(sets["modern_only"]),
            "union": len(sets["modern"] | sets["literary"]),
        },
        "samples": {
            "archaic_only": pick(arch),
            "overlap": pick(ov),
            "modern_only": pick(mod),
        },
        "checks": {
            "абазвався_in_archaic_only": "абазвався" in sets["archaic_only"],
            "абазвався_in_overlap": "абазвався" in sets["overlap"],
        },
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Split RU headwords: modern (DetCorpus) vs archaic (Afan-only)")
    p.add_argument("--modern-headwords", type=Path, default=DEFAULT_MODERN)
    p.add_argument("--literary-store", type=Path, default=None)
    p.add_argument("--literary-headwords", type=Path, default=None)
    p.add_argument("--write-archaic", action="store_true", help="Write ru-archaic-v0/headwords.v1.txt")
    p.add_argument("--export-literary", type=Path, default=None, help="Optional: dump full literary list")
    p.add_argument("--out-archaic", type=Path, default=DEFAULT_ARCHAIC_OUT)
    p.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = p.parse_args()

    literary_store = args.literary_store
    if literary_store is None and args.literary_headwords is None:
        literary_store = REPO / "lab/agent-stores/sss-ru-lexicon-v0"

    modern = _load_modern(args.modern_headwords.resolve())
    literary = _load_literary(
        store_dir=literary_store.resolve() if literary_store else None,
        literary_path=args.literary_headwords.resolve() if args.literary_headwords else None,
    )
    sets = split_sets(modern, literary)
    report = build_report(sets)

    if args.export_literary:
        write_headwords(
            args.export_literary,
            sorted(sets["literary"]),
            header="literary L2 export for split",
        )
        report["export_literary"] = str(args.export_literary.resolve())

    if args.write_archaic:
        args.out_archaic.parent.mkdir(parents=True, exist_ok=True)
        write_headwords(
            args.out_archaic,
            sorted(sets["archaic_only"]),
            header="archaic-only (Afan L2 minus DetCorpus modern)",
        )
        report["archaic_headwords_out"] = str(args.out_archaic.resolve())

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["counts"], ensure_ascii=False, indent=2))
    print(json.dumps(report["checks"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
