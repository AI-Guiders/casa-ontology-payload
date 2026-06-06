#!/usr/bin/env python3
"""Macro-tick phrase self-drive: trial plan → per-word analytic → compose (ADR-0035)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import _ensure_paths  # noqa: F401
from phrase_self_drive_core import run_phrase_self_drive_event
from runner_infra import LITERACY, bootstrap, lab_session

bootstrap(__file__)
_MICRO = Path(__file__).resolve().parent


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann")
    p.add_argument(
        "--goal",
        default="goal.read.phrase#lang.event.transitive.wash.v0",
        help="goal_id with optional #event_id suffix",
    )
    args = p.parse_args()

    lab = lab_session(LITERACY, micro_dir=_MICRO, store_id=args.store)
    lab.load()
    out = run_phrase_self_drive_event(lab.store_dir, lab.state, goal=args.goal)
    lab.save(sync_ltm=False)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    raise SystemExit(0 if out["wake_complete"] and out["word_count"] == len(out["words_analytic"]) else 1)


if __name__ == "__main__":
    main()
