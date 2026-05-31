#!/usr/bin/env python3
"""CLI: T_repair on prism_memory after damage."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.prisms.shared.prism_state_v0 import normalize_prisms, prism_memory, prism_hippo, prism_control, PRISM_MEMORY, PRISM_HIPPO, PRISM_CONTROL, set_active_prism
import argparse
import copy
import json
from pathlib import Path

from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms, memory_lattices, save_state
from casa.prisms.hippo.sss_damage_v0 import damage_memory_lattices
from casa.prisms.hippo.sss_repair_v0 import repair_field_state
from casa.prisms.memory.sss_stack_v0 import load_stack


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--stack", type=Path, default=Path("design/sss-lattice-stack.v0.json"))
    p.add_argument("--damage-lattice", default="L0_grapheme")
    p.add_argument("--damage-patches", type=int, default=6)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--allow-canonical", action="store_true")
    p.add_argument("--damage-only", action="store_true", help="damage without repair")
    args = p.parse_args()

    store = args.store_dir.resolve()
    path = store / "field_state.json"
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    stack = load_stack(args.stack)

    state = ensure_prisms(load_field_state(path))
    lattices = copy.deepcopy(memory_lattices(state))
    dmg = damage_memory_lattices(
        lattices,
        targets=[args.damage_lattice],
        count=args.damage_patches,
        seed=args.seed,
    )
    prism_memory(state)["lattices"] = lattices
    state.setdefault("sss", {})["lattices"] = lattices
    state["field_version"] = int(state.get("field_version") or 0) + 1
    state["sn"] = {**(state.get("sn") or {}), "mode": "repair"}

    report: dict = {"damage": dmg}
    if not args.damage_only:
        report["repair"] = repair_field_state(
            state,
            bundle,
            stack,
            allow_canonical=args.allow_canonical,
        )

    save_state(path, state)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
