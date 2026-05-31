#!/usr/bin/env python3
"""Lab store with control lattice stack + optional memory bundle."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import shutil
from pathlib import Path

from export_ltm_pack_v0 import export_pack  # type: ignore
from field_write import save_field_state  # type: ignore
from control_cylinders_v0 import migrate_control_stack  # type: ignore
from sss_cylinders_v0 import ensure_prisms  # type: ignore
from export_ltm_pack_v0 import control_lattice_ids  # type: ignore


def init_control_lab(
    store_dir: Path,
    bundle_path: Path,
    *,
    copies: int = 5,
) -> dict:
    store_dir.mkdir(parents=True, exist_ok=True)
    bundles = store_dir / "bundles"
    bundles.mkdir(parents=True, exist_ok=True)
    name = bundle_path.name
    dest = bundles / name
    if bundle_path.resolve() != dest.resolve():
        shutil.copy2(bundle_path, dest)

    bundle = json.loads(dest.read_text(encoding="utf-8"))
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    state.setdefault("store", {})["store_id"] = store_dir.name
    state["store"]["subsystem"] = "control-lab"

    state.setdefault("bundles", {})[name] = {
        "concept_count": len({c.get("concept_id") for c in bundle.get("claims", []) if c.get("concept_id")}),
        "claim_count": len(bundle.get("claims") or []),
        "edge_count": len((bundle.get("graph") or {}).get("edges") or []),
    }

    rep = migrate_control_stack(state, bundle, copies=copies)
    state["grid"] = {
        "width": 32,
        "height": 32,
        "cells": [[] for _ in range(32 * 32)],
        "source_bundle": name,
        "source_bundles": [name],
        "codec": "control_stack_v0",
    }
    fs = store_dir / "field_state.json"
    save_field_state(fs, state, compact=True)

    ltm = store_dir / "ltm"
    manifest = export_pack(state, ltm, lattice_ids=control_lattice_ids(state))

    mem = store_dir / "MEMORY.md"
    mem.write_text(
        "\n".join(
            [
                f"# {store_dir.name}",
                "",
                "Control lattice stack lab (DMN/SN/FPN/CEN on `prism_control`).",
                "",
                "Init:",
                "```bash",
                f"python tools/init_control_lab_v0.py --bundle {bundle_path.as_posix()}",
                "python tools/bench_control_stack_v0.py --store-dir "
                + str(store_dir.as_posix()),
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return {"store_dir": str(store_dir), "migrate": rep, "ltm_totals": manifest.get("totals")}


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Init control-lab store with prism_control")
    p.add_argument(
        "--store-dir",
        type=Path,
        default=root / "lab/agent-stores/control-lab-v0",
    )
    p.add_argument(
        "--bundle",
        type=Path,
        default=root / "lab/exp_l_v0/kb-math-concrete-schemas-l0.bundle.v1.json",
    )
    p.add_argument("--copies", type=int, default=5)
    args = p.parse_args()
    print(json.dumps(init_control_lab(args.store_dir, args.bundle, copies=args.copies), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
