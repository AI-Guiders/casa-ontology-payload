#!/usr/bin/env python3
"""Extract unique English headwords from plain-text corpus (folk tales, etc.)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import re
import unicodedata
from pathlib import Path

from sss_segment_v0 import norm_word  # type: ignore

# ASCII letters + apostrophe inside words (don't, king's)
WORD_RE = re.compile(r"[a-z]+(?:'[a-z]+)?", re.IGNORECASE)

EN_STOPWORDS = frozenset(
    """
    a an and are as at be been but by can could did do does doing done for from had has
    have he her hers him his i if in into is it its me my no nor not of on or our ours
    out she should so some such than that the their them then there these they this those
    to too up us was we were what when where which who whom why will with would you your yours
    """.split()
)

# Gutenberg boilerplate markers
GUTENBERG_START = re.compile(r"\*\*\*\s*START OF (THE|THIS) PROJECT GUTENBERG", re.I)
GUTENBERG_END = re.compile(r"\*\*\*\s*END OF (THE|THIS) PROJECT GUTENBERG", re.I)


def strip_gutenberg_boilerplate(text: str) -> str:
    start = GUTENBERG_START.search(text)
    end = GUTENBERG_END.search(text)
    if start and end and end.start() > start.end():
        return text[start.end() : end.start()]
    return text


def tokenize_english(text: str) -> list[str]:
    text = strip_gutenberg_boilerplate(text)
    text = unicodedata.normalize("NFC", text).lower()
    return [norm_word(m.group(0)) for m in WORD_RE.finditer(text)]


def extract_from_paths(paths: list[Path], *, min_len: int = 2, max_len: int = 32) -> dict:
    freq: dict[str, int] = {}
    per_file: dict[str, int] = {}
    for path in paths:
        raw = path.read_text(encoding="utf-8", errors="replace")
        words = tokenize_english(raw)
        unique_in_file: set[str] = set()
        for w in words:
            if min_len <= len(w) <= max_len and w.isascii():
                freq[w] = freq.get(w, 0) + 1
                unique_in_file.add(w)
        per_file[path.name] = len(unique_in_file)

    headwords = sorted(freq.keys())
    return {
        "files": len(paths),
        "unique_headwords": len(headwords),
        "total_tokens": sum(freq.values()),
        "per_file_unique": per_file,
        "freq": freq,
        "headwords": headwords,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Extract EN headwords from corpus .txt files")
    p.add_argument("--corpus-dir", type=Path, required=True)
    p.add_argument("--glob", type=str, default="*.txt")
    p.add_argument("--out", type=Path, required=True, help="Headwords list, one per line")
    p.add_argument("--min-len", type=int, default=2)
    p.add_argument("--min-freq", type=int, default=1, help="Drop hapax below this count")
    p.add_argument(
        "--stopwords",
        action="store_true",
        help="Drop common function words (the, and, of, …)",
    )
    p.add_argument("--report", type=Path, default=None)
    args = p.parse_args()

    paths = sorted(args.corpus_dir.glob(args.glob))
    if not paths:
        raise SystemExit(f"No files matching {args.glob} in {args.corpus_dir}")

    data = extract_from_paths(paths, min_len=args.min_len)
    freq = data["freq"]
    headwords = [w for w in data["headwords"] if freq[w] >= args.min_freq]
    if args.stopwords:
        headwords = [w for w in headwords if w not in EN_STOPWORDS]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(headwords) + "\n", encoding="utf-8")

    summary = {
        "corpus_dir": str(args.corpus_dir.resolve()),
        "files": [path.name for path in paths],
        "unique_headwords": len(headwords),
        "total_tokens": data["total_tokens"],
        "per_file_unique": data["per_file_unique"],
        "min_freq": args.min_freq,
        "out": str(args.out.resolve()),
        "top20": sorted(freq.items(), key=lambda x: (-x[1], x[0]))[:20],
    }
    if args.report:
        args.report.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
