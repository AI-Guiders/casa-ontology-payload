#!/usr/bin/env python3
"""Export headword list from an existing agent-store field_state (L2 tokens)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lexicon_headwords_v0 import export_headwords_from_store  # type: ignore


def main() -> None:
    p = argparse.ArgumentParser(description="Export L2 headwords from agent store")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--min-votes", type=int, default=1)
    args = p.parse_args()

    rep = export_headwords_from_store(args.store_dir, args.out, min_votes=args.min_votes)
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
