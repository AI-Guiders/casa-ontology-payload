#!/usr/bin/env python3
"""Bench SSS damage → cross-lattice repair (field-only vs +canonical)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from prism_state_v0 import normalize_prisms, prism_memory, prism_hippo, prism_control, PRISM_MEMORY, PRISM_HIPPO, PRISM_CONTROL, set_active_prism  # type: ignore
import argparse
import copy
import json
from pathlib import Path

from field_write import load_field_state, save_field_state  # type: ignore
from sss_cylinders_v0 import ensure_prisms, memory_lattices  # type: ignore
from sss_damage_v0 import damage_memory_lattices  # type: ignore
from sss_repair_v0 import repair_sss_memory  # type: ignore
from sss_stack_v0 import decode_lattice, lattice_digest, load_stack  # type: ignore


def _coverage(lattices: dict, bundle: dict, stack: dict) -> dict[str, dict]:
    out = {}
    for lat in stack.get("lattices") or []:
        lid = str(lat["id"])
        prefix = str(lat.get("concept_prefix") or "")
        expected = {
            c["concept_id"]
            for c in bundle.get("claims") or []
            if str(c.get("concept_id", "")).startswith(prefix)
        }
        if lid not in lattices or not expected:
            continue
        dec = decode_lattice(lattices[lid], min_votes=1)
        got = {c for c, _ in lattice_digest(dec, prefix=prefix)}
        out[lid] = {
            "expected": len(expected),
            "recovered": len(got & expected),
            "missing": sorted(expected - got),
            "hit": expected <= got,
        }
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--stack", type=Path, default=Path("design/sss-lattice-stack.v0.json"))
    p.add_argument("--damage-lattice", default="L0_grapheme")
    p.add_argument("--patch-w", type=int, default=10)
    p.add_argument("--patch-h", type=int, default=10)
    p.add_argument("--damage-patches", type=int, default=6)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--allow-canonical", action="store_true")
    p.add_argument("--write", action="store_true", help="persist repaired state")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    stack = load_stack(args.stack)
    path = args.store_dir / "field_state.json"
    state = ensure_prisms(load_field_state(path))
    baseline = _coverage(memory_lattices(state), bundle, stack)

    lattices = copy.deepcopy(memory_lattices(state))
    damage_report = damage_memory_lattices(
        lattices,
        targets=[args.damage_lattice],
        patch_w=args.patch_w,
        patch_h=args.patch_h,
        count=args.damage_patches,
        seed=args.seed,
    )
    after_damage = _coverage(lattices, bundle, stack)

    repair_report = repair_sss_memory(
        lattices,
        bundle,
        stack,
        allow_canonical=args.allow_canonical,
    )
    after_repair = _coverage(lattices, bundle, stack)

    report = {
        "store": str(args.store_dir.resolve()),
        "damage_lattice": args.damage_lattice,
        "damage": damage_report,
        "baseline": baseline,
        "after_damage": after_damage,
        "after_repair": after_repair,
        "repair": repair_report,
        "field_only_ok": repair_report["all_ok"],
        "mode": "field_only" if not args.allow_canonical else "field_plus_canonical",
    }

    if args.write:
        prism_memory(state)["lattices"] = lattices
        state.setdefault("sss", {})["lattices"] = lattices
        state["field_version"] = int(state.get("field_version") or 0) + 1
        state.setdefault("repair", {})["last_bench"] = report
        save_field_state(path, state)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
