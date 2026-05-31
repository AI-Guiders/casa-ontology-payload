#!/usr/bin/env python3
"""Rebuild agent store with SSS lattice stack (sss_lattice_stack_v1)."""

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
from casa.prisms.memory.stack import apply_z_compose, encode_sss_stack, load_stack


def rebuild_sss_store(
    store_dir: Path,
    bundle: dict,
    bundle_name: str,
    *,
    stack_path: Path | None = None,
    agent_id: str = "sss-lab",
    listen_passes: int = 3,
    apply_bridges: bool = True,
) -> dict:
    store_dir.mkdir(parents=True, exist_ok=True)
    (store_dir / "bundles").mkdir(exist_ok=True)
    bundle_path = store_dir / "bundles" / bundle_name
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    stack = load_stack(stack_path)
    copies = 4 + min(listen_passes, 12)
    lattices = encode_sss_stack(bundle, stack, copies=copies)
    bridge_report = (
        apply_z_compose(lattices, bundle, stack) if apply_bridges else {"composed": [], "count": 0}
    )

    path = store_dir / "field_state.json"
    state = load_field_state(path)
    if not state:
        state = new_field_state(agent_id=agent_id, cluster="sss")

    state["bundles"] = {
        bundle_name: {
            "concept_count": len({c.get("concept_id") for c in bundle.get("claims", []) if c.get("concept_id")}),
            "claim_count": len(bundle.get("claims") or []),
            "edge_count": len((bundle.get("graph") or {}).get("edges") or []),
            "content_hash": bundle_content_hash(bundle),
            "digest": {"listen_passes": listen_passes, "z_compose": bridge_report["count"]},
        }
    }
    state["claims_nav"] = build_claims_nav([(bundle_name, bundle)])
    state["subsystem"] = "sss"
    state["schema_version"] = "multi_prism_v1"
    state["sss"] = {
        "stack": str(stack_path or "design/prisms/memory/stack.json"),
        "lattices": lattices,
        "z_bridges": [b.get("id") for b in stack.get("z_bridges") or []],
        "active_lattice": "L0_grapheme",
        "listen_passes": listen_passes,
        "last_compose": bridge_report,
    }
    state["prisms"] = {
        "prism_memory": {
            "subsystem": "sss",
            "stack": state["sss"]["stack"],
            "lattices": lattices,
            "active_lattice": "L0_grapheme",
        },
        "prism_hippo": {
            "subsystem": "episodic",
            "lattices": {
                "H0_episode": {
                    "z_level": 0,
                    "width": 32,
                    "height": 32,
                    "cells": [[] for _ in range(1024)],
                    "concept_prefix": "episodic.",
                }
            },
            "episodes": [],
        },
    }
    state["sn"] = {"active_prism": "prism_memory", "active_lattice": "L0_grapheme", "mode": "wake"}
    state["consolidation"] = {"last_sleep_tick": 0, "episodes_merged_total": 0}
    state["grid"] = None
    state["field_version"] = int(state.get("field_version") or 0) + listen_passes
    save_field_state(path, state)
    return state


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--stack", type=Path, default=Path("design/prisms/memory/stack.json"))
    p.add_argument("--listen-passes", type=int, default=5)
    p.add_argument("--init", action="store_true")
    p.add_argument("--no-bridges", action="store_true")
    args = p.parse_args()

    store = args.store_dir.resolve()
    if args.init and store.exists():
        shutil.rmtree(store)

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    state = rebuild_sss_store(
        store,
        bundle,
        args.bundle.name,
        stack_path=args.stack,
        listen_passes=max(1, args.listen_passes),
        apply_bridges=not args.no_bridges,
    )
    sss = state.get("sss") or {}
    print(
        json.dumps(
            {
                "store": str(store),
                "schema": state.get("schema_version"),
                "field_version": state.get("field_version"),
                "lattices": list((sss.get("lattices") or {}).keys()),
                "z_compose": (sss.get("last_compose") or {}).get("count"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
