#!/usr/bin/env python3
"""Bench SSS: per-lattice coverage + z_compose."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.prisms.shared.field_write import load_field_state
from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms, memory_lattices
from casa.prisms.memory.sss_stack_v0 import apply_z_compose_v0, decode_lattice, lattice_digest, load_stack


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--stack", type=Path, default=Path("design/sss-lattice-stack.v0.json"))
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    stack = load_stack(args.stack)
    state = ensure_prisms(load_field_state(args.store_dir / "field_state.json"))
    lattices = memory_lattices(state)
    if not lattices:
        raise SystemExit("no memory lattices in field_state")

    layer_results = {}
    for lat in stack.get("lattices") or []:
        lid = str(lat["id"])
        prefix = str(lat.get("concept_prefix") or "")
        expected = sorted(
            {c["concept_id"] for c in bundle["claims"] if c["concept_id"].startswith(prefix)}
        )
        dec = decode_lattice(lattices[lid], min_votes=1)
        got = {c for c, _ in lattice_digest(dec, prefix=prefix)}
        exp = set(expected)
        layer_results[lid] = {
            "z_level": lat.get("z_level"),
            "hit": exp <= got,
            "expected": len(exp),
            "recovered": len(got & exp),
            "missing": sorted(exp - got),
        }

    compose = apply_z_compose_v0(lattices, bundle, stack)
    expected_compose = len(
        [
            e
            for e in (bundle.get("graph") or {}).get("edges") or []
            if e.get("relation") == "compose"
        ]
    )

    report = {
        "store": str(args.store_dir),
        "schema": state.get("schema_version"),
        "field_version": state.get("field_version"),
        "lattices": layer_results,
        "all_lattices_ok": all(r["hit"] for r in layer_results.values()),
        "z_compose": {
            "composed": compose["count"],
            "expected_edges": expected_compose,
            "items": compose.get("composed") or [],
        },
    }
    data = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(data, encoding="utf-8")
    print(data)


if __name__ == "__main__":
    main()
