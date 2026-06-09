#!/usr/bin/env python3
"""Ingest math L0 bundle → schema-math lattice on store state."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.domain.prism_ids import PRISM_MATH, PRISM_HIPPO, PRISM_CONTROL
from casa.domain.prism_wire import normalize_prisms, prism_block, prism_hippo, prism_control, set_active_prism
import argparse
import json
from pathlib import Path
from typing import Any

from casa.prisms.shared.lattice_names_v1 import SCHEMA_MATH
from casa.prisms.memory.f0_stack import encode_f0_lattice, load_f0_stack
from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.memory.memory_prisms import ensure_prisms, import_lattice_into_prism
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.shared.store_layout import field_state_path


def ingest_math_bundle(
    state: dict,
    bundle: dict,
    *,
    lattice_id: str = SCHEMA_MATH,
    stack_path: Path | None = None,
    copies: int = 5,
) -> dict[str, Any]:
    state = ensure_prisms(state)
    stack = load_f0_stack(stack_path)
    lat = encode_f0_lattice(bundle, lattice_id=lattice_id, stack=stack, copies=copies)
    import_lattice_into_prism(state, PRISM_MATH, lattice_id, lat, write_context="bootstrap")
    prism_block(state, PRISM_MATH)["active_lattice"] = lattice_id
    state["f0"] = {
        "stack": str(stack_path or Path("design/f0-math-lattice-stack.json")),
        "bundle_id": bundle.get("bundle_id"),
        "active_lattice": lattice_id,
    }
    state["sn"] = {
        **(state.get("sn") or {}),
        "active_subsystem": "first_signal_math",
        "active_f_lattice": lattice_id,
        "active_prism": PRISM_MATH,
    }
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return {
        "lattice_id": lattice_id,
        "bundle_id": bundle.get("bundle_id"),
        "token_cells": sum(len(c) for c in lat.get("cells") or []),
        "field_version": state["field_version"],
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Ingest kb-math L0 → schema-math")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--boot-ltm-only", action="store_true", help="Boot from ltm/ if no field_state")
    p.add_argument("--write", action="store_true")
    p.add_argument("--copies", type=int, default=5)
    args = p.parse_args()

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    fs = field_state_path(args.store_dir)
    if args.boot_ltm_only or not fs.is_file():
        state = boot_store(args.store_dir, prefer_field_state=False)["state"]
    else:
        state = ensure_prisms(load_field_state(fs))

    rep = ingest_math_bundle(state, bundle, copies=args.copies)
    if args.write:
        save_field_state(fs, state, compact=True)
        rep["written"] = str(fs)
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
