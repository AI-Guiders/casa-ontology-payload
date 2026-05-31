#!/usr/bin/env python3
"""Download third-party corpora used by the CASA lab (not tracked in git).

Raw datasets live under ``lab/corpus/**/source/`` (gitignored). This wrapper runs
the existing fetchers, which download the sources and rebuild the derived
headword / frequency / POS sidecars.

Licenses and provenance: see ``THIRD-PARTY-NOTICES.md``.

    python scripts/download_corpora.py            # all corpora
    python scripts/download_corpora.py --refresh  # re-download even if cached
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

JOBS: list[list[str]] = [
    ["tools/fetch_ru_frequency_headwords_v0.py"],
    ["tools/fetch_en_frequency_headwords_v0.py"],
    ["tools/fetch_ud_lemma_pos_v0.py", "--locale", "ru"],
    ["tools/fetch_ud_lemma_pos_v0.py", "--locale", "en"],
    ["scripts/fetch_en_folk_gutenberg_v0.py"],
]


def main() -> int:
    p = argparse.ArgumentParser(description="Download CASA third-party corpora")
    p.add_argument("--refresh", action="store_true", help="Re-download even if cached")
    args = p.parse_args()

    failed: list[str] = []
    for job in JOBS:
        cmd = [sys.executable, *job]
        if args.refresh and job[0].startswith("tools/fetch_"):
            cmd.append("--refresh")
        print(f"\n=== {' '.join(job)} ===", flush=True)
        if subprocess.run(cmd, cwd=str(ROOT)).returncode != 0:
            failed.append(" ".join(job))

    if failed:
        print("\nFAILED:\n  " + "\n  ".join(failed), file=sys.stderr)
        return 1
    print("\nAll corpora downloaded into lab/corpus/**/source/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
