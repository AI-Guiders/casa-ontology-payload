#!/usr/bin/env python3
"""Download RU lemma frequency list (DetCorpus 50k, CC0) → headwords + ipm sidecar."""

from __future__ import annotations

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

import argparse
import csv
import json
import re
import urllib.request
from pathlib import Path

from casa.prisms.memory.lexicon_headwords import write_headwords
from casa.prisms.memory.vocab import norm_word

DEFAULT_URL = (
    "https://raw.githubusercontent.com/Digital-Pushkin-Lab/"
    "Russian-Word-Frequency-Lists-for-Children/main/wordlist_detcorpus_50000.csv"
)
SOURCE_ID = "detcorpus-50k-cc0"
RU_LEMMA_RE = re.compile(r"^[а-яё]+(?:-[а-яё]+)?$", re.IGNORECASE)


def rel_to_root(path: Path, root: Path) -> str:
    """Repo-relative posix path for manifests (no absolute machine paths in tracked files)."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return resolved.as_posix()


def download_csv(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as resp:
        dest.write_bytes(resp.read())


def parse_frequency_csv(
    path: Path,
    *,
    min_ipm: float = 0.0,
    max_lemma_len: int = 32,
) -> tuple[list[str], list[dict]]:
    words: list[str] = []
    meta: list[dict] = []
    seen: set[str] = set()

    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lemma = norm_word((row.get("lemma") or "").strip())
            if not lemma or lemma in seen:
                continue
            if len(lemma) > max_lemma_len:
                continue
            if not RU_LEMMA_RE.match(lemma):
                continue
            try:
                ipm = float(row.get("ipm") or 0)
                abs_freq = int(float(row.get("abs_frequency") or 0))
            except ValueError:
                continue
            if ipm < min_ipm:
                continue
            seen.add(lemma)
            words.append(lemma)
            meta.append(
                {
                    "lemma": lemma,
                    "ipm": ipm,
                    "abs_frequency": abs_freq,
                    "rank": len(words),
                }
            )

    return words, meta


def main() -> None:
    root = REPO_ROOT
    p = argparse.ArgumentParser(description="Fetch RU frequency headwords (DetCorpus CC0)")
    p.add_argument("--url", default=DEFAULT_URL)
    p.add_argument(
        "--out",
        type=Path,
        default=root / "lab/corpus/ru-general/headwords.v1.txt",
    )
    p.add_argument(
        "--meta-out",
        type=Path,
        default=root / "lab/corpus/ru-general/frequency.ipm.v1.jsonl",
    )
    p.add_argument(
        "--csv-cache",
        type=Path,
        default=root / "lab/corpus/ru-general/source/detcorpus_50000.csv",
    )
    p.add_argument("--min-ipm", type=float, default=0.0)
    p.add_argument("--refresh", action="store_true", help="Re-download CSV even if cached")
    args = p.parse_args()

    if args.refresh or not args.csv_cache.is_file():
        print(f"Downloading {args.url} …", flush=True)
        download_csv(args.url, args.csv_cache)

    words, meta = parse_frequency_csv(args.csv_cache, min_ipm=args.min_ipm)
    if len(words) < 10_000:
        raise SystemExit(f"Too few Cyrillic lemmas: {len(words)}")

    write_headwords(
        args.out,
        words,
        header=f"ru-general frequency ({SOURCE_ID}, {len(words)} lemmas)",
    )

    args.meta_out.parent.mkdir(parents=True, exist_ok=True)
    with args.meta_out.open("w", encoding="utf-8") as f:
        for row in meta:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = root / "lab/corpus/ru-general/source.manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "corpus_id": "ru-general",
                "source_id": SOURCE_ID,
                "license": "CC0-1.0",
                "url": args.url,
                "unique_lemmas": len(words),
                "min_ipm": args.min_ipm,
                "headwords": rel_to_root(args.out, root),
                "meta": rel_to_root(args.meta_out, root),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "source": SOURCE_ID,
                "unique_headwords": len(words),
                "out": str(args.out.resolve()),
                "meta_out": str(args.meta_out.resolve()),
                "top5": meta[:5],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
