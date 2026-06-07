#!/usr/bin/env python3
"""Restore a living agent from life-archive snapshot (trained memory, not cold bootstrap)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.cli.bootstrap_agent_self_tier import bootstrap_agent_self_tier
from casa.prisms.shared.store_layout import default_agent_store
from casa.prisms.shared.store_mirror import (
    detect_git_lfs_pointer,
    resolve_life_archive_store,
    restore_store_to_agent_dir,
)


def _scan_lfs_pointers(store_dir: Path) -> list[str]:
    warnings: list[str] = []
    for pattern in ("**/*.pt", "**/*.db"):
        for path in store_dir.glob(pattern):
            if detect_git_lfs_pointer(path):
                warnings.append(str(path.relative_to(store_dir)))
                if len(warnings) >= 5:
                    return warnings
    return warnings


def restore_agent_life(
    store_dir: Path,
    *,
    source_store: Path,
    force: bool = False,
    seed_self_if_missing: bool = True,
) -> dict:
    rep = restore_store_to_agent_dir(source_store, store_dir, force=force)
    lfs_warn = _scan_lfs_pointers(store_dir)
    if lfs_warn:
        rep["lfs_pointer_warning"] = lfs_warn
        rep["lfs_hint"] = "Run: git lfs pull (inside life-archive clone)"

    journal_dir = store_dir / "journal"
    has_journal = journal_dir.is_dir() and any(journal_dir.rglob("entries.jsonl"))
    if seed_self_if_missing and not has_journal:
        rep["self_tier"] = bootstrap_agent_self_tier(store_dir, skip_if_journal_exists=True)
    else:
        rep["self_tier"] = {"skipped": True, "reason": "journal_from_snapshot"}

    rep["trained"] = (store_dir / "ltm").is_dir() or (store_dir / "agent_field.db").is_file()
    rep["next"] = (
        "python -m casa.prisms.control.agent_sn_cen_tick --store-dir "
        + str(store_dir)
        + ' --query "Привет"'
    )
    return rep


def main() -> None:
    p = argparse.ArgumentParser(
        description="Restore agent life from life-archive store/ snapshot"
    )
    p.add_argument("--store-dir", type=Path, default=None, help="Destination agents/<id>/")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--from-life-archive",
        type=Path,
        metavar="DIR",
        help="Path to von-neumann-life-archive clone (uses DIR/store/)",
    )
    src.add_argument(
        "--from-store",
        type=Path,
        metavar="DIR",
        help="Path directly to store/ mirror",
    )
    p.add_argument("--force", action="store_true", help="Replace non-empty destination store")
    p.add_argument(
        "--no-seed-self",
        action="store_true",
        help="Do not bootstrap Self tier when journal missing",
    )
    args = p.parse_args()

    if args.from_life_archive:
        source = resolve_life_archive_store(args.from_life_archive)
    else:
        source = args.from_store.resolve()

    rep = restore_agent_life(
        args.store_dir or default_agent_store(),
        source_store=source,
        force=args.force,
        seed_self_if_missing=not args.no_seed_self,
    )
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 1 if rep.get("lfs_pointer_warning") else 0


if __name__ == "__main__":
    raise SystemExit(main())
