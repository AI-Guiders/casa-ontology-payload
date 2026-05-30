#!/usr/bin/env python3
"""Migrate agent store / field_state to control lattice stack (cyl_control)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from control_cylinders_v0 import migrate_control_stack  # type: ignore
from export_ltm_pack_v0 import export_pack  # type: ignore
from field_write import load_field_state, save_field_state  # type: ignore
from sss_cylinders_v0 import ensure_prisms  # type: ignore


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_bundle(store_dir: Path, bundle_name: str | None) -> dict | None:
    if not bundle_name:
        return None
    p = store_dir / "bundles" / bundle_name
    if not p.is_file():
        p = Path(bundle_name)
    if not p.is_file():
        raise FileNotFoundError(bundle_name)
    return _read_json(p)


def main() -> None:
    p = argparse.ArgumentParser(description="Migrate DMN/SN/FPN/CEN to control lattice stack")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--bundle", default=None, help="Bundle filename under store/bundles or path")
    p.add_argument("--layout", type=Path, default=Path("design/layout.v0.json"))
    p.add_argument("--copies", type=int, default=5)
    p.add_argument("--export-ltm", action="store_true", help="Write control lattices to store/ltm/ctrl/")
    p.add_argument("--wm-mode", default="explore")
    p.add_argument("--wm-goal", default="")
    args = p.parse_args()

    store = args.store_dir.resolve()
    fs_path = store / "field_state.json"
    if fs_path.is_file():
        state = ensure_prisms(load_field_state(fs_path))
    else:
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        state.setdefault("store", {})["store_id"] = store.name

    bundle = _load_bundle(store, args.bundle) if args.bundle else None
    layout = _read_json(args.layout) if args.layout.is_file() else None

    if bundle is None and not state.get("grid"):
        raise SystemExit("Provide --bundle or field_state with legacy grid")

    report = migrate_control_stack(
        state,
        bundle,
        layout=layout,
        copies=args.copies,
        wm_mode=args.wm_mode,
        wm_goal=args.wm_goal,
    )
    save_field_state(fs_path, state, compact=True)
    report["field_state"] = str(fs_path)

    if args.export_ltm:
        ltm_dir = store / "ltm"
        from export_ltm_pack_v0 import control_lattice_ids  # type: ignore

        manifest = export_pack(
            state,
            ltm_dir,
            store_dir=store,
            lattice_ids=control_lattice_ids(state),
        )
        report["ltm_totals"] = manifest.get("totals")

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
