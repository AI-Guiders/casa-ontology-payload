#!/usr/bin/env python3
"""Rewrite field_state.json from multi_cylinder_v1 → multi_prism_v1 (one-time lab ops)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa.domain.prism_wire import normalize_prisms, wire_used_legacy_format
from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.shared.store_layout import field_state_path


def migrate_store(store_dir: Path, *, dry_run: bool = False) -> dict:
    store_dir = store_dir.resolve()
    fs = field_state_path(store_dir)
    if not fs.is_file():
        raise SystemExit(f"no field_state: {fs}")
    before = json.loads(fs.read_text(encoding="utf-8"))
    if not wire_used_legacy_format(before):
        return {"store": store_dir.name, "migrated": False, "reason": "already multi_prism_v1"}
    state = load_field_state(fs, store_dir=store_dir)
    normalize_prisms(state)
    if dry_run:
        return {"store": store_dir.name, "migrated": True, "dry_run": True}
    save_field_state(fs, state, compact=True)
    return {"store": store_dir.name, "migrated": True, "field_state": str(fs)}


def main() -> None:
    p = argparse.ArgumentParser(description="Migrate legacy cylinder wire in field_state.json")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    print(json.dumps(migrate_store(args.store_dir, dry_run=args.dry_run), indent=2))


if __name__ == "__main__":
    main()
