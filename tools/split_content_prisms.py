#!/usr/bin/env python3
"""MP-5: move RU lexicon + math lattices from prism_memory to domain content prisms."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.domain.content_prism_split import split_content_prisms
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.shared.store_layout import field_state_path, use_compact_field_state


def main() -> None:
    p = argparse.ArgumentParser(description="Split prism_memory lattices → prism_lang_ru / prism_math")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--dry-run", action="store_true", help="Report only; do not write")
    p.add_argument(
        "--compact-persist",
        action="store_true",
        help="After write, flush ltm/ per content prism",
    )
    args = p.parse_args()

    fs = field_state_path(args.store_dir)
    state = ensure_prisms(load_field_state(fs))
    report = split_content_prisms(state, move=not args.dry_run)

    if not args.dry_run:
        save_field_state(fs, state, compact=use_compact_field_state(args.store_dir))
        report["written"] = str(fs)
        if args.compact_persist:
            from casa.prisms.shared.compact_persist import compact_persist_store

            report["compact_persist"] = compact_persist_store(
                args.store_dir, state, reason="split_content_prisms"
            )

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
