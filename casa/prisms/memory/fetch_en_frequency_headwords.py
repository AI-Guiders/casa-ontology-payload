#!/usr/bin/env python3
"""Download EN lemma frequency (OpenSubtitles 50k, MIT) → headwords + ipm sidecar."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import re
import urllib.request
from pathlib import Path

from casa.prisms.memory.lexicon_headwords import write_headwords
from casa.prisms.memory.vocab import norm_word

DEFAULT_URL = (
    "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/en/en_50k.txt"
)
SOURCE_ID = "opensubtitles-en-50k"
EN_LEMMA_RE = re.compile(r"^[a-z]+(?:[-'][a-z]+)?$")


def rel_to_root(path: Path, root: Path) -> str:
    """Repo-relative posix path for manifests (no absolute machine paths in tracked files)."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return resolved.as_posix()


def download_txt(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as resp:
        dest.write_bytes(resp.read())


def parse_frequency_txt(
    path: Path,
    *,
    min_count: int = 1,
    max_lemma_len: int = 32,
    max_lemmas: int = 50_000,
) -> tuple[list[str], list[dict], int]:
    """Parse hermitdave word<TAB>count lines; ipm from corpus token total."""
    words: list[str] = []
    meta: list[dict] = []
    seen: set[str] = set()
    total_tokens = 0
    raw_rows: list[tuple[str, int]] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        lemma = norm_word(parts[0])
        try:
            count = int(parts[1])
        except ValueError:
            continue
        if count < min_count:
            continue
        if not lemma or lemma in seen:
            continue
        if len(lemma) > max_lemma_len:
            continue
        if not EN_LEMMA_RE.match(lemma):
            continue
        seen.add(lemma)
        raw_rows.append((lemma, count))
        total_tokens += count
        if len(raw_rows) >= max_lemmas:
            break

    if total_tokens <= 0:
        raise SystemExit("Empty corpus token count")

    for rank, (lemma, count) in enumerate(raw_rows, start=1):
        ipm = count / total_tokens * 1_000_000.0
        words.append(lemma)
        meta.append(
            {
                "lemma": lemma,
                "ipm": round(ipm, 4),
                "abs_frequency": count,
                "rank": rank,
            }
        )

    return words, meta, total_tokens


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Fetch EN frequency headwords (OpenSubtitles 50k MIT)")
    p.add_argument("--url", default=DEFAULT_URL)
    p.add_argument(
        "--out",
        type=Path,
        default=root / "lab/corpus/en-general/headwords.v1.txt",
    )
    p.add_argument(
        "--meta-out",
        type=Path,
        default=root / "lab/corpus/en-general/frequency.ipm.v1.jsonl",
    )
    p.add_argument(
        "--txt-cache",
        type=Path,
        default=root / "lab/corpus/en-general/source/en_50k.txt",
    )
    p.add_argument("--min-count", type=int, default=1)
    p.add_argument("--refresh", action="store_true", help="Re-download even if cached")
    args = p.parse_args()

    if args.refresh or not args.txt_cache.is_file():
        print(f"Downloading {args.url} …", flush=True)
        download_txt(args.url, args.txt_cache)

    words, meta, total_tokens = parse_frequency_txt(args.txt_cache, min_count=args.min_count)
    if len(words) < 5_000:
        raise SystemExit(f"Too few EN lemmas: {len(words)}")

    write_headwords(
        args.out,
        words,
        header=f"en-general frequency ({SOURCE_ID}, {len(words)} lemmas)",
    )

    args.meta_out.parent.mkdir(parents=True, exist_ok=True)
    with args.meta_out.open("w", encoding="utf-8") as f:
        for row in meta:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = root / "lab/corpus/en-general/source.manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "corpus_id": "en-general",
                "source_id": SOURCE_ID,
                "license": "MIT (hermitdave/FrequencyWords, OpenSubtitles-derived)",
                "url": args.url,
                "unique_lemmas": len(words),
                "corpus_tokens": total_tokens,
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
                "corpus_tokens": total_tokens,
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
