#!/usr/bin/env python3
"""One-shot: L0_grapheme monolith → L0_grapheme_cyrl + L0_grapheme_latn; fix active_lattice + stack path."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path
from typing import Any

from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.shared.store_layout import use_compact_field_state
from casa.prisms.memory.grapheme_ingest import migrate_legacy_l0_grapheme
from casa.prisms.shared.prism_state import normalize_prisms, prism_memory
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices

STACK_TOML = "design/sss-lattice-stack.toml"
DEFAULT_L0_CYRL = "L0_grapheme_cyrl"
DEFAULT_L0_LATN = "L0_grapheme_latn"


def _default_l0(store_dir: Path, state: dict) -> str:
    locale = str((state.get("store") or {}).get("locale") or "").lower()
    if locale == "en":
        return DEFAULT_L0_LATN
    name = store_dir.name.lower()
    if "en" in name and "ru" not in name:
        return DEFAULT_L0_LATN
    return DEFAULT_L0_CYRL


def patch_state_metadata(state: dict, store_dir: Path) -> list[str]:
    changes: list[str] = []
    target = _default_l0(store_dir, state)

    def _fix_active(obj: dict, label: str) -> None:
        if str(obj.get("active_lattice") or "") == "L0_grapheme":
            obj["active_lattice"] = target
            changes.append(f"{label}.active_lattice→{target}")

    _fix_active(state.setdefault("sn", {}), "sn")
    mem = prism_memory(state)
    _fix_active(mem, "prism_memory")
    sss = state.setdefault("sss", {})
    if str(sss.get("active_lattice") or "") == "L0_grapheme":
        sss["active_lattice"] = target
        changes.append(f"sss.active_lattice→{target}")

    for holder in (mem, sss):
        stack = holder.get("stack")
        if isinstance(stack, str) and stack.endswith("prisms/memory/stack.json"):
            holder["stack"] = STACK_TOML
            changes.append("stack→toml")

    if state.get("schema_version") == "multi_cylinder_v1":
        normalize_prisms(state)
        changes.append("schema→multi_prism_v1")

    return changes


def migrate_field_state(path: Path, *, compact: bool) -> dict[str, Any] | None:
    store_dir = path.parent
    before = path.read_text(encoding="utf-8")
    state = load_field_state(path)
    state = ensure_prisms(state)
    meta_changes = patch_state_metadata(state, store_dir)
    default_script: str = "latn" if _default_l0(store_dir, state) == DEFAULT_L0_LATN else "cyrl"
    mig = migrate_legacy_l0_grapheme(state, default_script=default_script)  # type: ignore[arg-type]
    lattices = memory_lattices(state)
    has_legacy = "L0_grapheme" in lattices
    after = json.dumps(state, ensure_ascii=False, sort_keys=True)
    before_norm = json.dumps(json.loads(before), ensure_ascii=False, sort_keys=True)
    if after == before_norm and not meta_changes and not mig.get("migrated"):
        return None
    save_field_state(path, state, compact=compact)
    return {
        "store": store_dir.name,
        "meta": meta_changes,
        "split": mig,
        "has_legacy_lattice": has_legacy,
        "l0_lattices": sorted(k for k in lattices if k.startswith("L0_grapheme")),
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Split L0_grapheme across agent stores + agent-core")
    p.add_argument("--stores-root", type=Path, default=Path("lab/agent-stores"))
    p.add_argument("--core-root", type=Path, default=Path("lab/agent-core"))
    p.add_argument("--compact", action="store_true", help="Compact JSON for large lexicon stores")
    args = p.parse_args()

    paths: list[Path] = []
    if args.stores_root.is_dir():
        paths.extend(sorted(args.stores_root.glob("*/field_state.json")))
    if args.core_root.is_dir():
        paths.extend(sorted(args.core_root.glob("*/field_state.json")))

    n = 0
    for fs in paths:
        rep = migrate_field_state(
            fs,
            compact=args.compact or use_compact_field_state(fs.parent),
        )
        if rep:
            n += 1
            print(json.dumps(rep, ensure_ascii=False))
    print(f"migrated {n} field_state files")


if __name__ == "__main__":
    main()
