#!/usr/bin/env python3
"""Remigrate L2_word monolith → L2_word_XX shards (required before ltm export on large stores)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa.prisms.memory.l2_remigrate import needs_l2_remigrate, remigrate_l2_from_monolith
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.shared.store_layout import field_state_path, use_compact_field_state


def main() -> None:
    p = argparse.ArgumentParser(description="L2 monolith → sharded lattices")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, default=None, help="JSON report path")
    p.add_argument("--copies", type=int, default=3)
    p.add_argument("--num-shards", type=int, default=64)
    p.add_argument("--keep-monolith", action="store_true", help="Do not clear L2_word cells")
    p.add_argument("--write", action="store_true", help="Save field_state.json after remigrate")
    args = p.parse_args()

    store_dir = args.store_dir.resolve()
    fs = field_state_path(store_dir)
    state = ensure_prisms(load_field_state(fs, store_dir=store_dir))
    if not needs_l2_remigrate(state) and not args.write:
        rep = {"status": "noop", "reason": "needs_l2_remigrate=false"}
    else:
        rep = remigrate_l2_from_monolith(
            state,
            copies=args.copies,
            num_shards=args.num_shards,
            clear_monolith=not args.keep_monolith,
        )
    if args.write:
        save_field_state(fs, state, compact=use_compact_field_state(store_dir))
        rep["written"] = str(fs)

    text = json.dumps(rep, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
