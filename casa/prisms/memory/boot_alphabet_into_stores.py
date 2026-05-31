#!/usr/bin/env python3
"""Merge alphabet core into agent stores with empty L0 grapheme lattices."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from casa.prisms.memory.alphabet_core import verify_alphabet_on_l0
from casa.prisms.memory.boot_core_ltm import default_alphabet_core_ltm_dir, merge_alphabet_l0_from_ltm
from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.shared.store_layout import field_state_path
from casa.prisms.memory.grapheme_ingest import L0_CYRL_ID, L0_LATN_ID
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.memory.nca_codec import tokens_from_lattice


def l0_token_count(state: dict) -> dict[str, int]:
    lat = memory_lattices(ensure_prisms(state))
    out: dict[str, int] = {}
    for lid in (L0_CYRL_ID, L0_LATN_ID):
        L = lat.get(lid) or {}
        out[lid] = len(tokens_from_lattice(L)) if L else 0
    return out


def needs_alphabet(state: dict, *, min_tokens: int = 8) -> bool:
    counts = l0_token_count(state)
    return counts.get(L0_CYRL_ID, 0) < min_tokens or counts.get(L0_LATN_ID, 0) < min_tokens


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Boot alphabet core into agent stores")
    p.add_argument("--stores-root", type=Path, default=root / "lab/agent-stores")
    p.add_argument("--alphabet-ltm", type=Path, default=None)
    p.add_argument("--all", action="store_true", help="Merge into every store (not only empty L0)")
    p.add_argument("--compact", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    altm = (args.alphabet_ltm or default_alphabet_core_ltm_dir(root=root)).resolve()
    if not (altm / "pack.manifest.json").is_file():
        raise SystemExit(f"missing alphabet pack: {altm}")

    reports: list[dict] = []
    for fs in sorted(args.stores_root.glob("*/field_state.json")):
        state = ensure_prisms(load_field_state(fs))
        if not args.all and not needs_alphabet(state):
            continue
        before = l0_token_count(state)
        if args.dry_run:
            reports.append({"store": fs.parent.name, "dry_run": True, "before": before})
            continue
        boot = merge_alphabet_l0_from_ltm(state, altm)
        verify = verify_alphabet_on_l0(state)
        after = l0_token_count(state)
        compact = args.compact or fs.parent.name.startswith("sss-")
        save_field_state(field_state_path(fs.parent), state, compact=compact)
        reports.append(
            {
                "store": fs.parent.name,
                "before": before,
                "after": after,
                "verify_pass": bool(verify.get("pass")),
                "boot": boot.get("import", {}).get("loaded"),
            }
        )

    print(json.dumps({"merged": len(reports), "stores": reports}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
