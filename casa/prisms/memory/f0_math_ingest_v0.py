#!/usr/bin/env python3
"""Ingest math L0 bundle → schema-math lattice on store state."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from prism_state_v0 import normalize_prisms, prism_memory, prism_hippo, prism_control, PRISM_MEMORY, PRISM_HIPPO, PRISM_CONTROL, set_active_prism  # type: ignore
import argparse
import json
from pathlib import Path
from typing import Any

from lattice_names_v1 import SCHEMA_MATH  # type: ignore
from f0_stack_v0 import encode_f0_lattice, load_f0_stack  # type: ignore
from field_write import load_field_state, save_field_state  # type: ignore
from sss_cylinders_v0 import ensure_prisms, memory_lattices  # type: ignore
from store_boot_v0 import boot_store  # type: ignore
from store_layout_v0 import field_state_path  # type: ignore


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
    lattices = memory_lattices(state)
    lattices[lattice_id] = lat
    prism_memory(state)["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices
    state["f0"] = {
        "stack": str(stack_path or Path("design/f0-math-lattice-stack.v0.json")),
        "bundle_id": bundle.get("bundle_id"),
        "active_lattice": lattice_id,
    }
    state["sn"] = {
        **(state.get("sn") or {}),
        "active_subsystem": "first_signal_math",
        "active_f_lattice": lattice_id,
        "active_prism": "prism_memory",
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
