#!/usr/bin/env python3
"""Build technical EN/RU headword lists from repo text + seed files."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import re
from pathlib import Path

from casa.prisms.memory.lexicon_headwords import EN_WORD_RE, RU_WORD_RE, read_headwords, write_headwords
from casa.prisms.memory.vocab import norm_word

_CONCEPT_WORD_RE = re.compile(r"lang\.word\.([a-zа-яё0-9_\-]+)", re.IGNORECASE)
_IDENTIFIER_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b")
_CYRILLIC_ID_RE = re.compile(r"\b[А-Яа-яЁё_][А-Яа-яЁё0-9_]{2,}\b")

EN_STOP = frozenset(
    """
    the and for are was with this that from have has had not but you your our their
    will can may also into its than them then when what which who how all any each
    """.split()
)

SCAN_SUFFIXES = {".md", ".json", ".cs", ".py", ".toml", ".txt"}


def _scan_file(path: Path, locale: str, freq: dict[str, int]) -> None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    if locale == "ru":
        for m in RU_WORD_RE.finditer(text.lower()):
            w = norm_word(m.group(0))
            if len(w) >= 2:
                freq[w] = freq.get(w, 0) + 1
        for m in _CYRILLIC_ID_RE.finditer(text):
            w = norm_word(m.group(0).lower())
            if len(w) >= 2:
                freq[w] = freq.get(w, 0) + 1
    else:
        for m in EN_WORD_RE.finditer(text.lower()):
            w = norm_word(m.group(0))
            if len(w) >= 2 and w not in EN_STOP:
                freq[w] = freq.get(w, 0) + 1
        for m in _IDENTIFIER_RE.finditer(text):
            w = norm_word(m.group(0).lower())
            if len(w) >= 2 and w not in EN_STOP:
                freq[w] = freq.get(w, 0) + 1
    for m in _CONCEPT_WORD_RE.finditer(text):
        w = norm_word(m.group(1).replace("_", ""))
        if w:
            freq[w] = freq.get(w, 0) + 3


def build_tech_headwords(
    *,
    locale: str,
    scan_roots: list[Path],
    seeds: list[Path],
    min_freq: int = 1,
    min_len: int = 2,
    max_len: int = 48,
) -> list[str]:
    freq: dict[str, int] = {}
    for seed in seeds:
        if seed.is_file():
            for w in read_headwords(seed):
                freq[w] = freq.get(w, 0) + 10

    for root in scan_roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in SCAN_SUFFIXES:
                continue
            if any(part.startswith(".") for part in path.parts):
                continue
            if "node_modules" in path.parts or "bin" in path.parts or "obj" in path.parts:
                continue
            _scan_file(path, locale, freq)

    return sorted(
        w
        for w, c in freq.items()
        if c >= min_freq and min_len <= len(w) <= max_len
    )


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Build technical headwords (EN or RU)")
    p.add_argument("--locale", choices=("en", "ru"), required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--seed", type=Path, action="append", default=[])
    p.add_argument("--scan", type=Path, action="append", default=[])
    p.add_argument("--min-freq", type=int, default=1)
    args = p.parse_args()

    default_seeds = [root / f"lab/corpus/{args.locale}-tech/seed.v1.txt"]
    seeds = list(args.seed) or default_seeds
    default_scan = [
        root / "design",
        root / "tools",
        root / "apps",
        root / "lab",
        root.parent / "cascade-ide" / "docs",
        root.parent.parent.parent / "knowledge",
    ]
    scan_roots = list(args.scan) if args.scan else default_scan

    words = build_tech_headwords(
        locale=args.locale,
        scan_roots=scan_roots,
        seeds=seeds,
        min_freq=args.min_freq,
    )
    write_headwords(args.out, words, header=f"tech {args.locale}")
    rep = {"locale": args.locale, "unique_headwords": len(words), "out": str(args.out.resolve())}
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
