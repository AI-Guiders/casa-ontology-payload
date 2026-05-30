#!/usr/bin/env python3
"""Import store/ltm/*.ltm → field_state memory lattices."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from prism_state_v0 import prism_control, prism_memory  # type: ignore

from control_cylinders_v0 import ensure_control_cylinder  # type: ignore
from field_write import load_field_state, save_field_state  # type: ignore
from ltm_pack_v0 import read_ltm  # type: ignore
from sss_cylinders_v0 import ensure_cylinders, memory_lattices  # type: ignore


def _resolve_ltm_path(ltm_dir: Path, lid: str, entry: dict[str, Any]) -> Path:
    p = entry.get("path")
    if p:
        cand = Path(p)
        if cand.is_file():
            return cand
        cand = ltm_dir.parent / p
        if cand.is_file():
            return cand
    for ext in ("", ".zst", ".gz"):
        for sub in ("l2", "l1", "l0", "l3", "h0", "ctrl", "lat"):
            cand = ltm_dir / sub / f"{lid}.ltm{ext}"
            if cand.is_file():
                return cand
    raise FileNotFoundError(f"no .ltm for {lid!r}")


def import_pack(
    state: dict,
    ltm_dir: Path,
    *,
    manifest: dict | None = None,
) -> dict[str, Any]:
    state = ensure_cylinders(state)
    state = ensure_control_cylinder(state)
    mem_lattices = memory_lattices(state)
    ctrl_lattices = prism_control(state)["lattices"]
    manifest = manifest or json.loads((ltm_dir / "pack.manifest.json").read_text(encoding="utf-8"))
    loaded: list[str] = []
    loaded_control: list[str] = []

    for lid, entry in (manifest.get("lattices") or {}).items():
        path = _resolve_ltm_path(ltm_dir, lid, entry if isinstance(entry, dict) else {})
        decoded = read_ltm(path)
        meta = entry.get("meta") if isinstance(entry, dict) else {}
        merged = {**(meta or {}), **decoded}
        if str(lid).startswith("lattice_"):
            ctrl_lattices[lid] = merged
            loaded_control.append(lid)
        else:
            mem_lattices[lid] = merged
            loaded.append(lid)

    prism_memory(state)["lattices"] = mem_lattices
    prism_control(state)["lattices"] = ctrl_lattices
    state.setdefault("sss", {})["lattices"] = mem_lattices
    if manifest.get("l2_sharding"):
        state["l2_sharding"] = manifest["l2_sharding"]
    if manifest.get("nca"):
        state["nca"] = manifest["nca"]
    if manifest.get("field_version") is not None:
        state["field_version"] = manifest["field_version"]
    return {
        "loaded": loaded,
        "loaded_control": loaded_control,
        "lattice_count": len(loaded),
        "control_lattice_count": len(loaded_control),
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Import ltm/ pack into field_state")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--ltm-dir", type=Path, default=None)
    p.add_argument("--write", action="store_true", help="Save field_state.json after import")
    p.add_argument("--compact", action="store_true", default=True)
    args = p.parse_args()

    ltm_dir = args.ltm_dir or (args.store_dir / "ltm")
    path = args.store_dir / "field_state.json"
    if path.is_file():
        state = ensure_cylinders(load_field_state(path))
    else:
        state = ensure_cylinders({"schema_version": "multi_prism_v1", "field_version": 0})

    rep = import_pack(state, ltm_dir)
    if args.write:
        save_field_state(path, state, compact=args.compact)
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
