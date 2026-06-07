#!/usr/bin/env python3
"""Ingest RU-α material→verbal train moments (Galperin bridge)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from casa._paths import REPO_ROOT
from casa.cli.ingest_verbal_moment import run_verbal_moment_plan

_CLASS = REPO_ROOT / "lessons/ru-material-verbal"
_PLAN = _CLASS / "data/material-verbal-moment-plan-v1.json"
_PROBE = REPO_ROOT / "lab/visual-curriculum/probe_material_verbal_ru.py"


def _store_dir(store_id: str) -> Path:
    return (REPO_ROOT / "agents" / store_id).resolve()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--plan", type=Path, default=_PLAN)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--probe", action="store_true", help="Run train probe (no inline remember)")
    p.add_argument("--sync-life", action="store_true")
    args = p.parse_args()

    store = _store_dir(args.store)
    summary = run_verbal_moment_plan(
        store,
        plan_path=args.plan,
        source="ingest_material_verbal",
        dry_run=args.dry_run,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.probe and not args.dry_run:
        cmd = [sys.executable, str(_PROBE), "--store", args.store]
        proc = subprocess.run(cmd, cwd=str(REPO_ROOT))
        if proc.returncode != 0:
            raise SystemExit(proc.returncode)

    if args.sync_life and not args.dry_run:
        sync = REPO_ROOT / "tools/sync_life_archive.py"
        if sync.is_file():
            proc = subprocess.run(
                [
                    sys.executable,
                    str(sync),
                    "--store-dir",
                    str(store),
                    "snapshot",
                    "-m",
                    "life: RU-α material-verbal ingest",
                ],
                cwd=str(REPO_ROOT),
            )
            raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
