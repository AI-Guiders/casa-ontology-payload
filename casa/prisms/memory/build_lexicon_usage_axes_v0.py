#!/usr/bin/env python3
"""Build lexicon_axes.v0.jsonl from frequency sidecar (RU DetCorpus / EN OpenSubtitles)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.prisms.memory.lexicon_headwords_v0 import read_headwords
from casa.prisms.memory.lexicon_usage_axes_v0 import (
    SOURCE_DETCORPUS,
    SOURCE_OPENSUB_EN,
    axes_report,
    build_modern_axes_from_frequency_jsonl,
    overlay_archaic_lemmas,
    write_axes_jsonl,
)
from casa.prisms.shared.store_layout_v0 import CORPUS_QUAD

REPO = Path(__file__).resolve().parent.parent
DEFAULT_RU_FREQ = REPO / "lab/corpus/ru-general-v0/frequency.ipm.v1.jsonl"
DEFAULT_EN_FREQ = REPO / "lab/corpus/en-general-v0/frequency.ipm.v1.jsonl"
DEFAULT_ARCHAIC = REPO / "lab/corpus/ru-archaic-v0/headwords.v1.txt"

CORPUS_FREQ: dict[str, tuple[Path, str, str | None]] = {
    "ru-general": (DEFAULT_RU_FREQ, SOURCE_DETCORPUS, "fetch_ru_frequency_headwords_v0.py"),
    "en-general": (DEFAULT_EN_FREQ, SOURCE_OPENSUB_EN, "fetch_en_frequency_headwords_v0.py"),
}


def main() -> None:
    p = argparse.ArgumentParser(description="Build lexicon usage axes JSONL")
    p.add_argument("--corpus", choices=tuple(CORPUS_FREQ.keys()), default="ru-general")
    p.add_argument("--frequency-jsonl", type=Path, default=None)
    p.add_argument("--archaic-headwords", type=Path, default=None, help="RU: optional archaic-only list")
    p.add_argument("--include-archaic", action="store_true", help="Merge ru-archaic-v0 headwords")
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--copy-to-store", type=Path, default=None)
    args = p.parse_args()

    spec = CORPUS_QUAD[args.corpus]
    default_freq, source_id, fetch_hint = CORPUS_FREQ[args.corpus]
    freq_path = args.frequency_jsonl or default_freq
    out = args.out or (REPO / spec.headwords_rel).parent / "lexicon_axes.v0.jsonl"

    if not freq_path.is_file():
        raise SystemExit(f"Missing {freq_path} — run tools/{fetch_hint}")

    axes = build_modern_axes_from_frequency_jsonl(freq_path.resolve(), source=source_id)
    archaic_n = 0
    if args.corpus == "ru-general":
        arch_path = args.archaic_headwords
        if args.include_archaic and arch_path is None and DEFAULT_ARCHAIC.is_file():
            arch_path = DEFAULT_ARCHAIC
        if arch_path and arch_path.is_file():
            archaic_n = overlay_archaic_lemmas(axes, set(read_headwords(arch_path)))

    write_axes_jsonl(out, axes)
    report = {
        "corpus": args.corpus,
        "source": source_id,
        "out": str(out.resolve()),
        "modern_lemmas": len(axes) - archaic_n,
        "archaic_overlay": archaic_n,
        **axes_report(axes),
    }

    if args.copy_to_store:
        store_axes = args.copy_to_store / "lexicon_axes.v0.jsonl"
        write_axes_jsonl(store_axes, axes)
        report["store_axes"] = str(store_axes.resolve())

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
