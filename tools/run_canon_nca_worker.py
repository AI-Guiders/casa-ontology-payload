#!/usr/bin/env python3
"""Standalone canon NCA worker — body artifacts only; agent owns checkpoint commit."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.prisms.memory.canon_nca_train import (
    list_canon_nca_status,
    read_train_complete,
    run_pending_canon_nca_trains,
)
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.field_write import load_field_state
from casa.prisms.shared.nca_registry import load_registry
from casa.prisms.shared.canon_lattice_policy import is_canon_nca_lattice
from casa.prisms.shared.lattice_names_v1 import canonical_lattice_id
from casa.prisms.shared.store_layout import field_state_path


def _load_state(store_dir: Path) -> dict:
    fs = field_state_path(store_dir)
    if fs.is_file():
        return ensure_prisms(load_field_state(fs))
    return ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})


def _canon_pending_count(store_dir: Path) -> int:
    reg = load_registry(store_dir)
    pending = [canonical_lattice_id(str(x)) for x in (reg.get("pending") or [])]
    return sum(1 for lid in pending if is_canon_nca_lattice(lid))


def _has_trainable_pending(store_dir: Path) -> bool:
    reg = load_registry(store_dir)
    pending = [canonical_lattice_id(str(x)) for x in (reg.get("pending") or [])]
    for lid in pending:
        if not is_canon_nca_lattice(lid):
            continue
        if read_train_complete(store_dir, lid) is not None:
            continue
        return True
    return False


def run_batch(
    store_dir: Path,
    *,
    max_jobs: int,
    device: str,
) -> dict:
    state = _load_state(store_dir)
    report = run_pending_canon_nca_trains(
        store_dir,
        state,
        max_jobs=max_jobs,
        device=device,
        agent_commit=False,
    )
    report["pending_after"] = _canon_pending_count(store_dir)
    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--max-jobs", type=int, default=1)
    p.add_argument("--device", default="cpu")
    p.add_argument(
        "--loop",
        action="store_true",
        help="Poll pending queue until empty (or --max-rounds); does not block agent process",
    )
    p.add_argument("--interval", type=float, default=30.0, help="Seconds between loop polls")
    p.add_argument("--max-rounds", type=int, default=0, help="0 = unlimited in --loop mode")
    p.add_argument("--status-only", action="store_true", help="Print queue status and exit")
    args = p.parse_args()

    store_dir = args.store_dir.resolve()
    if args.status_only:
        state = _load_state(store_dir)
        print(json.dumps(list_canon_nca_status(state, store_dir), ensure_ascii=False, indent=2))
        return 0

    rounds = 0
    while True:
        report = run_batch(
            store_dir,
            max_jobs=max(1, args.max_jobs),
            device=args.device,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if not args.loop:
            return 0
        rounds += 1
        if not _has_trainable_pending(store_dir):
            return 0
        if args.max_rounds > 0 and rounds >= args.max_rounds:
            return 0
        time.sleep(max(1.0, float(args.interval)))


if __name__ == "__main__":
    raise SystemExit(main())
