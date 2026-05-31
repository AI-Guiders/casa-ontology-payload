#!/usr/bin/env python3
"""Ingest POS claims onto L3_phrase: lang.word.* → pos.* (no new organ)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path
from typing import Any

from casa.prisms.shared.codec_grid_v0 import Grid
from casa.prisms.memory.entity_hub_ingest_v0 import _ensure_l3_lattice
from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.shared.lattice_names_v1 import PHRASES
from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms, memory_lattices
from casa.prisms.memory.sss_stack_v0 import _place_token, decode_lattice
from casa.prisms.memory.sss_vocab_v0 import norm_word
from casa.prisms.shared.store_boot_v0 import boot_store
from casa.prisms.shared.store_layout_v0 import field_state_path


def _surface_concept(word: str) -> str:
    return f"lang.word.{norm_word(word)}"


def _pos_concept(pos_id: str) -> str:
    pid = (pos_id or "").strip().lower()
    if pid.startswith("pos."):
        return pid
    tag = pid.upper().replace(" ", "_")
    return f"pos.{tag.lower()}"


def ingest_pos_claims(
    state: dict,
    bundle: dict,
    *,
    lattice_id: str = PHRASES,
    copies: int = 4,
) -> dict[str, Any]:
    state = ensure_prisms(state)
    lat = _ensure_l3_lattice(state)
    g = Grid(width=int(lat["width"]), height=int(lat["height"]), cells=lat["cells"])

    claims = list(bundle.get("claims") or [])
    edge_count = 0
    pos_nodes: set[str] = set()
    lemma_count = 0

    for row in claims:
        lemma = norm_word(str(row.get("lemma") or row.get("word") or ""))
        if not lemma:
            continue
        pos_id = _pos_concept(str(row.get("pos_id") or row.get("pos") or ""))
        if not pos_id.startswith("pos."):
            continue
        sid = _surface_concept(lemma)
        g = _place_token(g, f"C:{pos_id}", f"C:{pos_id}", copies=copies, radius=5)
        pos_nodes.add(pos_id)
        tok = f"E:{sid}|has_pos|{pos_id}"
        g = _place_token(g, tok, tok, copies=max(2, copies // 2), radius=4)
        edge_count += 1
        lemma_count += 1

    lat["cells"] = g.cells
    lattices = memory_lattices(state)
    lattices[lattice_id] = lat
    state.setdefault("sss", {})["lattices"] = lattices
    state["pos_claims"] = {
        "bundle_id": bundle.get("bundle_id"),
        "lattice_id": lattice_id,
        "lemma_count": lemma_count,
    }
    state["field_version"] = int(state.get("field_version") or 0) + 1

    dec = decode_lattice(lat, min_votes=1)
    return {
        "lattice_id": lattice_id,
        "bundle_id": bundle.get("bundle_id"),
        "lemmas": lemma_count,
        "pos_nodes": len(pos_nodes),
        "edges_placed": edge_count,
        "l3_concepts": len(dec.get("concept_ids") or []),
        "l3_edges": len(dec.get("edges") or []),
        "field_version": state["field_version"],
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Ingest POS claims bundle → phrases")
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

    rep = ingest_pos_claims(state, bundle, copies=args.copies)
    if args.write:
        save_field_state(fs, state, compact=True)
        rep["written"] = str(fs)
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
