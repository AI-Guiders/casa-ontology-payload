#!/usr/bin/env python3
"""Attach prism_control (seeded stack) to every agent store with field_state.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from control_cylinders_v0 import has_control_stack, migrate_control_stack  # type: ignore
from export_ltm_pack_v0 import control_lattice_ids, export_pack  # type: ignore
from field_write import load_field_state, save_field_state  # type: ignore
from sss_cylinders_v0 import ensure_prisms  # type: ignore

STORES_ROOT = Path("lab/agent-stores")
SKIP_IF_CONTROL = True


def main() -> None:
    p = argparse.ArgumentParser(description="Migrate control stack on all agent stores")
    p.add_argument("--stores-root", type=Path, default=STORES_ROOT)
    p.add_argument("--copies", type=int, default=4)
    p.add_argument("--export-ltm", action="store_true", default=True)
    p.add_argument("--force", action="store_true", help="Re-migrate even if prism_control exists")
    args = p.parse_args()

    root = args.stores_root.resolve()
    reports: list[dict] = []

    for fs in sorted(root.glob("*/field_state.json")):
        store = fs.parent
        state = ensure_prisms(load_field_state(fs))
        if SKIP_IF_CONTROL and not args.force and has_control_stack(state):
            reports.append({"store": store.name, "skipped": "already_has_control"})
            continue

        bundle = None
        bundles_dir = store / "bundles"
        if bundles_dir.is_dir():
            first = next(bundles_dir.glob("*.json"), None)
            if first:
                bundle = json.loads(first.read_text(encoding="utf-8"))

        layout = None
        grid = state.get("grid")
        if grid and grid.get("cells"):
            layout_path = Path("design/layout.v0.json")
            if layout_path.is_file():
                layout = json.loads(layout_path.read_text(encoding="utf-8"))

        rep = migrate_control_stack(
            state,
            bundle,
            layout=layout,
            copies=args.copies,
        )
        save_field_state(fs, state, compact=store.name.startswith("sss-"))

        if args.export_ltm:
            ids = control_lattice_ids(state)
            if ids:
                export_pack(state, store / "ltm", store_dir=store, lattice_ids=ids)

        rep["store"] = store.name
        reports.append(rep)

    print(json.dumps({"migrated": reports}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
