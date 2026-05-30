#!/usr/bin/env python3
"""Extract unique Russian headwords from plain-text corpus (.txt)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lexicon_headwords_v0 import tokenize_text, write_headwords  # type: ignore


def extract_from_paths(
    paths: list[Path],
    *,
    min_len: int = 2,
    max_len: int = 32,
    min_freq: int = 1,
) -> dict:
    freq: dict[str, int] = {}
    per_file: dict[str, int] = {}
    for path in paths:
        raw = path.read_text(encoding="utf-8", errors="replace")
        unique_in_file: set[str] = set()
        for w in tokenize_text(raw, locale="ru"):
            if min_len <= len(w) <= max_len:
                freq[w] = freq.get(w, 0) + 1
                unique_in_file.add(w)
        per_file[path.name] = len(unique_in_file)

    headwords = sorted(w for w, c in freq.items() if c >= min_freq)
    return {
        "files": len(paths),
        "unique_headwords": len(headwords),
        "total_tokens": sum(freq.values()),
        "per_file_unique": per_file,
        "headwords": headwords,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Extract RU headwords from corpus .txt files")
    p.add_argument("--corpus-dir", type=Path, required=True)
    p.add_argument("--glob", type=str, default="*.txt")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--min-len", type=int, default=2)
    p.add_argument("--max-len", type=int, default=32)
    p.add_argument("--min-freq", type=int, default=1)
    p.add_argument("--report", type=Path, default=None)
    args = p.parse_args()

    paths = sorted(args.corpus_dir.glob(args.glob))
    if not paths:
        raise SystemExit(f"No files matching {args.glob!r} in {args.corpus_dir}")

    rep = extract_from_paths(
        paths,
        min_len=args.min_len,
        max_len=args.max_len,
        min_freq=args.min_freq,
    )
    write_headwords(args.out, rep["headwords"], header=f"corpus {args.corpus_dir.name}")
    out_rep = {k: v for k, v in rep.items() if k != "headwords"}
    out_rep["out"] = str(args.out.resolve())
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(out_rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out_rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
