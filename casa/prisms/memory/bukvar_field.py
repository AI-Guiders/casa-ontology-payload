#!/usr/bin/env python3
"""SSS lab store: layered sign memory in cylinder (codec sss_v0 / bukvar_v0 scaffold)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import shutil
from pathlib import Path

from casa.prisms.shared.field_write import (
    build_claims_nav,
    bundle_content_hash,
    load_field_state,
    new_field_state,
    save_field_state,
)
from casa.prisms.memory.bukvar_codec_v0 import encode_bukvar_bundle


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rebuild_bukvar_store(
    store_dir: Path,
    bundle: dict,
    bundle_name: str,
    layout: dict,
    *,
    agent_id: str = "bukvar-lab-v0",
    listen_passes: int = 1,
) -> dict:
    store_dir.mkdir(parents=True, exist_ok=True)
    (store_dir / "bundles").mkdir(exist_ok=True)
    bundle_path = store_dir / "bundles" / bundle_name
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    path = store_dir / "field_state.json"
    state = load_field_state(path)
    if not state:
        state = new_field_state(agent_id=agent_id, cluster="language-bukvar")

    copies = 4 + min(listen_passes, 12)
    grid = encode_bukvar_bundle(bundle, layout, copies=copies)
    nav = build_claims_nav([(bundle_name, bundle)])

    state["bundles"] = {
        bundle_name: {
            "concept_count": len({c.get("concept_id") for c in bundle.get("claims", []) if c.get("concept_id")}),
            "claim_count": len(bundle.get("claims") or []),
            "edge_count": len((bundle.get("graph") or {}).get("edges") or []),
            "content_hash": bundle_content_hash(bundle),
            "digest": {"listen_passes": listen_passes},
        }
    }
    state["claims_nav"] = nav
    state["grid"] = {
        "width": grid["width"],
        "height": grid["height"],
        "cells": grid["cells"],
        "source_bundle": bundle_name,
        "source_bundles": [bundle_name],
        "codec": "sss_v0",
        "subsystem": "sss",
        "layout": "design/layout.v1.json",
        "union": False,
    }
    state["field_version"] = int(state.get("field_version") or 0) + listen_passes
    state["layout_id"] = "layout.v1"
    save_field_state(path, state)
    return state


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--layout", type=Path, default=Path("design/layout.v1.json"))
    p.add_argument("--listen-passes", type=int, default=3, help="simulate repeated listen (more token copies)")
    p.add_argument("--init", action="store_true", help="clear store before rebuild")
    args = p.parse_args()

    store = args.store_dir.resolve()
    if args.init and store.exists():
        shutil.rmtree(store)

    layout = _read_json(args.layout)
    bundle = _read_json(args.bundle)
    name = args.bundle.name
    state = rebuild_bukvar_store(
        store,
        bundle,
        name,
        layout,
        listen_passes=max(1, args.listen_passes),
    )
    print(
        json.dumps(
            {
                "store": str(store),
                "field_version": state.get("field_version"),
                "concepts": state["bundles"][name]["concept_count"],
                "codec": state["grid"]["codec"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
