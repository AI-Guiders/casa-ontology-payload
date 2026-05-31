#!/usr/bin/env python3
"""Rebuild union field from all bundles in agent store."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

from field_write import list_store_bundles, load_field_state, rebuild_union_field, save_field_state  # type: ignore


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--layout", type=Path, default=Path("design/layout.v0.json"))
    p.add_argument("--concept-mode", default="section")
    args = p.parse_args()

    store = args.store_dir.resolve()
    layout = json.loads(args.layout.read_text(encoding="utf-8"))
    path = store / "field_state.json"
    state = load_field_state(path)
    loaded_names = {n for n, _ in list_store_bundles(state, store)}
    for stale in list((state.get("bundles") or {}).keys()):
        if stale not in loaded_names:
            del state["bundles"][stale]
    state = rebuild_union_field(state, store_dir=store, layout=layout, concept_mode=args.concept_mode)
    save_field_state(path, state)
    names = (state.get("grid") or {}).get("source_bundles") or []
    print(json.dumps({"union_bundles": names, "claims_nav": len(state.get("claims_nav") or []), "field_version": state.get("field_version")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
