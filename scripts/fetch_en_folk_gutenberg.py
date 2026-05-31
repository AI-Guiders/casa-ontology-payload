#!/usr/bin/env python3
"""Download Project Gutenberg sources for en-folk corpus (not tracked in git)."""

from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SOURCES = (
    (
        "grimm-fairy-tales.gutenberg.txt",
        "https://www.gutenberg.org/cache/epub/17038/pg17038.txt",
    ),
    (
        "jacobs-english-fairy-tales.gutenberg.txt",
        "https://www.gutenberg.org/cache/epub/2591/pg2591.txt",
    ),
)


def main() -> int:
    p = argparse.ArgumentParser(description="Fetch EN folk Gutenberg texts into lab/corpus/en-folk/source/")
    p.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "lab/corpus/en-folk/source",
    )
    p.add_argument("--refresh", action="store_true")
    args = p.parse_args()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, url in SOURCES:
        dest = out_dir / name
        if dest.is_file() and not args.refresh:
            print(f"skip (exists): {dest.relative_to(ROOT)}")
            continue
        print(f"fetch {url} -> {dest.relative_to(ROOT)}")
        with urllib.request.urlopen(url, timeout=120) as resp:
            dest.write_bytes(resp.read())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
