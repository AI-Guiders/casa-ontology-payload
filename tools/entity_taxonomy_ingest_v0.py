#!/usr/bin/env python3
"""Ingest entity taxonomy: entity.* → instanceOf → entity.animal|plant|… on L3."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from codec_grid_v0 import Grid  # type: ignore
from entity_hub_ingest_v0 import _ensure_l3_lattice  # type: ignore
from field_write import load_field_state, save_field_state  # type: ignore
from sss_cylinders_v0 import ensure_prisms, memory_lattices  # type: ignore
from sss_stack_v0 import _place_token, decode_lattice  # type: ignore
from store_boot_v0 import boot_store  # type: ignore
from store_layout_v0 import field_state_path  # type: ignore


def ingest_entity_taxonomy(
    state: dict,
    bundle: dict,
    *,
    lattice_id: str = "L3_phrase",
    copies: int = 4,
) -> dict[str, Any]:
    state = ensure_prisms(state)
    lat = _ensure_l3_lattice(state)
    g = Grid(width=int(lat["width"]), height=int(lat["height"]), cells=lat["cells"])

    type_ids = {str(t.get("entity_id") or "") for t in bundle.get("types") or []}
    edge_count = 0
    instance_count = 0

    for row in bundle.get("types") or []:
        tid = str(row.get("entity_id") or "")
        if not tid.startswith("entity."):
            continue
        g = _place_token(g, f"C:{tid}", f"C:{tid}", copies=copies, radius=5)
        type_ids.add(tid)

    for row in bundle.get("instances") or []:
        eid = str(row.get("entity_id") or "")
        parent = str(row.get("instance_of") or "")
        if not eid.startswith("entity.") or not parent.startswith("entity."):
            continue
        g = _place_token(g, f"C:{eid}", f"C:{eid}", copies=max(2, copies // 2), radius=4)
        g = _place_token(g, f"C:{parent}", f"C:{parent}", copies=copies, radius=5)
        tok = f"E:{eid}|instanceOf|{parent}"
        g = _place_token(g, tok, tok, copies=max(2, copies // 2), radius=4)
        edge_count += 1
        instance_count += 1

    lat["cells"] = g.cells
    lattices = memory_lattices(state)
    lattices[lattice_id] = lat
    state.setdefault("sss", {})["lattices"] = lattices
    state["entity_taxonomy"] = {
        "bundle_id": bundle.get("bundle_id"),
        "lattice_id": lattice_id,
        "types": len(type_ids),
        "instances": instance_count,
    }
    state["field_version"] = int(state.get("field_version") or 0) + 1

    dec = decode_lattice(lat, min_votes=1)
    return {
        "lattice_id": lattice_id,
        "bundle_id": bundle.get("bundle_id"),
        "types": len(type_ids),
        "instances": instance_count,
        "edges_placed": edge_count,
        "l3_concepts": len(dec.get("concept_ids") or []),
        "l3_edges": len(dec.get("edges") or []),
        "field_version": state["field_version"],
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Ingest entity taxonomy bundle → L3")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--boot-ltm-only", action="store_true")
    p.add_argument("--write", action="store_true")
    p.add_argument("--copies", type=int, default=4)
    args = p.parse_args()

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    fs = field_state_path(args.store_dir)
    if args.boot_ltm_only or not fs.is_file():
        state = boot_store(args.store_dir, prefer_field_state=False)["state"]
    else:
        state = ensure_prisms(load_field_state(fs))

    rep = ingest_entity_taxonomy(state, bundle, copies=args.copies)
    if args.write:
        save_field_state(fs, state, compact=True)
        rep["written"] = str(fs)
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
