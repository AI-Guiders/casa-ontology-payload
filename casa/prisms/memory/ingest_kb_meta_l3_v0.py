#!/usr/bin/env python3
"""Ingest KB meta concepts (meta.*) and graph edges onto L3_phrase."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path
from typing import Any

from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.memory.ortho_field_v0 import imprint_edge, imprint_l3_concept
from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms
from casa.prisms.shared.store_boot_v0 import boot_store
from casa.prisms.shared.store_layout_v0 import field_state_path


def ingest_kb_meta_l3(state: dict, bundle: dict, *, copies: int = 5) -> dict[str, Any]:
    state = ensure_prisms(state)
    concepts = 0
    edges = 0

    for claim in bundle.get("claims") or []:
        cid = str(claim.get("concept_id") or "").strip()
        if not cid:
            continue
        imprint_l3_concept(state, cid, copies=copies)
        concepts += 1

    for node in (bundle.get("graph") or {}).get("nodes") or []:
        cid = str(node.get("id") or "").strip()
        if cid and cid not in {str(c.get("concept_id")) for c in bundle.get("claims") or []}:
            imprint_l3_concept(state, cid, copies=max(2, copies - 1))
            concepts += 1

    for edge in (bundle.get("graph") or {}).get("edges") or []:
        src = str(edge.get("src") or "")
        rel = str(edge.get("relation") or "")
        dst = str(edge.get("dst") or "")
        if src and rel and dst:
            imprint_edge(state, src, rel, dst, copies=copies)
            edges += 1

    state.setdefault("kb_meta_l3", {})["bundle_id"] = bundle.get("bundle_id")
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return {
        "bundle_id": bundle.get("bundle_id"),
        "concepts_placed": concepts,
        "edges_placed": edges,
        "field_version": state["field_version"],
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Ingest meta.freq.* KB onto L3")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--write", action="store_true")
    p.add_argument("--copies", type=int, default=5)
    args = p.parse_args()

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    fs = field_state_path(args.store_dir)
    state = ensure_prisms(load_field_state(fs)) if fs.is_file() else boot_store(args.store_dir)["state"]

    rep = ingest_kb_meta_l3(state, bundle, copies=args.copies)
    if args.write:
        save_field_state(fs, state, compact=True)
        rep["written"] = str(fs.resolve())
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
