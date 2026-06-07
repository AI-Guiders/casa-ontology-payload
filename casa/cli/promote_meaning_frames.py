#!/usr/bin/env python3
"""Promote journal-stable meaning frames into semantics bundle."""

from __future__ import annotations

import argparse
import json

from casa._paths import REPO_ROOT
from casa.domain.meaning_authoring import promote_frame_from_journal


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--min-occurrences", type=int, default=2)
    args = p.parse_args()

    store = (REPO_ROOT / "agents" / args.store).resolve()
    summary = promote_frame_from_journal(store, min_occurrences=args.min_occurrences, dry_run=args.dry_run)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
