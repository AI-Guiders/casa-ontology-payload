#!/usr/bin/env python3
"""Smoke: prism_control lattices + sn_cen infer from field."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import subprocess
import sys
from pathlib import Path

from casa.prisms.control.cylinders import control_lattices, has_control_stack
from casa.prisms.shared.lattice_names_v1 import missing_control_lattices
from casa.prisms.shared.field_write import decode_field_grid, load_field_state
from casa.prisms.memory.memory_prisms import ensure_prisms


def main() -> None:
    p = argparse.ArgumentParser(description="Bench control lattice stack migration")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--min-votes", type=int, default=1)
    p.add_argument(
        "--structure-only",
        action="store_true",
        help="Pass when all control lattices exist (no DMN concepts / sn_cen infer required)",
    )
    args = p.parse_args()

    store = args.store_dir.resolve()
    fs = store / "field_state.json"
    if not fs.is_file():
        raise SystemExit(f"missing {fs}")

    state = ensure_prisms(load_field_state(fs))
    ok_stack = has_control_stack(state)
    lats = control_lattices(state) if ok_stack else {}
    missing = missing_control_lattices(lats)

    decoded = None
    dmn_concepts = 0
    if ok_stack:
        decoded = decode_field_grid(state, min_votes=args.min_votes)
        dmn_concepts = len(decoded.get("concept_ids") or [])

    infer_ok = False
    infer_detail = "skipped"
    control_ext = None
    if ok_stack and dmn_concepts > 0:
        from casa.prisms.control.tick import run_control_extensions

        cids = list(decoded.get("concept_ids") or []) if decoded else []
        control_ext = run_control_extensions(
            prior_digest=cids[: max(1, len(cids) // 2)],
            current_digest=cids,
            goal=cids[:3],
        ).to_dict()

    out = Path(__file__).resolve().parent.parent / "lab/sn_cen_out" / f"{store.name}_control_smoke.json"
    bundle = next((store / "bundles").glob("*.json"), None)
    if bundle and ok_stack and not missing:
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).parent / "sn_cen_infer.py"),
                "--from-field",
                "--store-dir",
                str(store),
                "--session",
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent),
        )
        infer_ok = proc.returncode == 0
        infer_detail = proc.stderr.strip() or proc.stdout.strip()[:400]
    else:
        infer_detail = "skipped"

    stack_ok = ok_stack and not missing and dmn_concepts > 0
    extensions_ok = control_ext is not None and control_ext.get("sparse_ratio", 1.0) <= 1.0

    report = {
        "store": str(store),
        "control_stack": ok_stack,
        "lattices": sorted(lats.keys()),
        "missing": sorted(missing),
        "dmn_concept_count": dmn_concepts,
        "control_extensions": control_ext,
        "infer_ok": infer_ok,
        "infer_detail": infer_detail if not infer_ok else str(out),
    }
    if args.structure_only:
        report["pass"] = ok_stack and not missing
    else:
        report["pass"] = stack_ok and extensions_ok and infer_ok
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
