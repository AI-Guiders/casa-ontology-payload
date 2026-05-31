#!/usr/bin/env python3
"""Rewrite field_state.json: cylinders/cyl_* → prisms/prism_*."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.shared.prism_state import normalize_prisms


def main() -> None:
    p = argparse.ArgumentParser(description="Migrate prism keys in all agent stores")
    p.add_argument("--stores-root", type=Path, default=Path("lab/agent-stores"))
    p.add_argument("--compact", action="store_true", help="Compact JSON for large lexicon stores")
    args = p.parse_args()

    n = 0
    for fs in sorted(args.stores_root.glob("*/field_state.json")):
        state = load_field_state(fs)
        raw_before = json.dumps(state, ensure_ascii=False, sort_keys=True)
        normalize_prisms(state)
        raw_after = json.dumps(state, ensure_ascii=False, sort_keys=True)
        if raw_before != raw_after:
            save_field_state(fs, state, compact=args.compact or fs.parent.name.startswith("sss-"))
            n += 1
            print(fs.parent.name, state.get("schema_version"))
    print(f"migrated {n} stores")


if __name__ == "__main__":
    main()
