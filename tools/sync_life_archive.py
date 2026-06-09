#!/usr/bin/env python3
"""Snapshot living agent store into von-neumann-life-archive."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.cli.resync_agent_store import resync_agent_store
from casa.prisms.shared.store_layout import default_agent_store


def main() -> int:
    p = argparse.ArgumentParser(description="Sync agents/<id>/ → life-archive store/")
    sub = p.add_subparsers(dest="cmd", required=True)

    snap = sub.add_parser("snapshot", help="Re-sync store + mirror into life-archive")
    snap.add_argument("--store-dir", type=Path, default=None)
    snap.add_argument(
        "--archive-dir",
        type=Path,
        required=True,
        help="Path to von-neumann-life-archive clone",
    )
    snap.add_argument("--message", default="life: snapshot")
    snap.add_argument("--skip-migrate", action="store_true")

    args = p.parse_args()
    store_dir = (args.store_dir or default_agent_store()).resolve()
    archive_dir = Path(args.archive_dir).resolve()

    if args.cmd == "snapshot":
        rep = resync_agent_store(
            store_dir,
            life_archive_dir=archive_dir,
            message=args.message,
            skip_migrate=args.skip_migrate,
            mirror_archive=True,
        )
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
