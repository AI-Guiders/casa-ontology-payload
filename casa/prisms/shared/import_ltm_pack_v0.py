#!/usr/bin/env python3
"""Import store/ltm/*.ltm → field_state memory lattices."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path
from typing import Any

from casa.prisms.shared.prism_state_v0 import prism_control, prism_memory

from casa.prisms.control.cylinders_v0 import ensure_control_cylinder
from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.shared.ltm_pack_v0 import read_ltm
from casa.prisms.shared.store_paths_v1 import ltm_scan_subdirs, resolve_ltm_file
from casa.prisms.memory.sss_cylinders_v0 import ensure_cylinders, memory_lattices


def _resolve_ltm_path(ltm_dir: Path, lid: str, entry: dict[str, Any]) -> Path:
    return resolve_ltm_file(ltm_dir, lid, entry)


def _ltm_lattice_id(path: Path) -> str:
    name = path.name
    for suffix in (".ltm.zst", ".ltm.gz", ".ltm"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def import_ltm_dir_scan(state: dict, ltm_dir: Path) -> dict[str, Any]:
    """Load every *.ltm under ltm/ (canonical + legacy tiers)."""
    state = ensure_cylinders(state)
    state = ensure_control_cylinder(state)
    mem_lattices = memory_lattices(state)
    loaded: list[str] = []
    for subdir in ltm_scan_subdirs(ltm_dir):
        for path in sorted(subdir.glob("*.ltm*")):
            if not path.is_file():
                continue
            lid = _ltm_lattice_id(path)
            if not lid or lid in mem_lattices:
                continue
            mem_lattices[lid] = read_ltm(path)
            loaded.append(lid)
    prism_memory(state)["lattices"] = mem_lattices
    state.setdefault("sss", {})["lattices"] = mem_lattices
    return {"scanned": loaded, "scan_count": len(loaded)}


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
    p.add_argument(
        "--scan-ltm",
        action="store_true",
        help="Also load all ltm/l0|l1|l2|l3/*.ltm not listed in manifest",
    )
    p.add_argument(
        "--fresh",
        action="store_true",
        help="Ignore existing field_state.json (rebuild from ltm only)",
    )
    args = p.parse_args()

    ltm_dir = args.ltm_dir or (args.store_dir / "ltm")
    path = args.store_dir / "field_state.json"
    if args.fresh or not path.is_file():
        state = ensure_cylinders({"schema_version": "multi_prism_v1", "field_version": 0})
    else:
        state = ensure_cylinders(load_field_state(path))

    rep = import_pack(state, ltm_dir)
    if args.scan_ltm:
        rep["scan"] = import_ltm_dir_scan(state, ltm_dir)
    if args.write:
        save_field_state(path, state, compact=args.compact)
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
