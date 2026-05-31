#!/usr/bin/env python3
"""Listen bridge: keyboard modifiers (Shift, Caps Lock) ↔ ortho processes (ADR-0003 + ADR-0008)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path
from typing import Any

from casa.prisms.memory.ortho_field_v0 import (
    L3_ID,
    imprint_capitalize_bootstrap,
    imprint_edge,
    imprint_l3_concept,
    l3_process_edges,
    l3_process_ids,
)
from casa.prisms.memory.ortho_process_v0 import (
    PROC_CAPITALIZE,
    PROC_LOWER,
    PROC_SENTENCE_CASE,
    PROC_UPPER,
)
from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms

# Cross-layer listen edges (L3): input modality ↔ ortho Process
BRIDGE_EDGES: list[tuple[str, str, str]] = [
    ("input.modality.layout", "has_layer", "input.modality.base_layer"),
    ("input.modality.base_layer", "standard_register", "ortho.display.lowercase_register"),
    ("input.modality.base_layer", "complements", "input.modality.shift_layer"),
    ("ortho.display.lowercase_register", "keyboard_path", "input.modality.base_layer"),
    ("proc.grapheme.lower", "emergent_inverse", PROC_CAPITALIZE),
    ("proc.grapheme.lower", "distinct_from", "ortho.display.lowercase_register"),
    ("input.modality.shift_layer", "surface_effect", PROC_CAPITALIZE),
    ("modifier.shift", "selects_layer", "input.modality.shift_layer"),
    ("modifier.caps_lock", "latch_like", "input.modality.shift_layer"),
    ("modifier.caps_lock", "toggles", "input.modality.caps_latch"),
    ("input.modality.caps_latch", "selects_layer", "input.modality.shift_layer"),
    ("modifier.caps_lock", "surface_effect", PROC_UPPER),
    ("modifier.caps_lock", "produces", "ortho.display.all_caps"),
    ("ortho.display.all_caps", "same_as", PROC_UPPER),
    ("proc.word.upper", "fold", PROC_CAPITALIZE),
    ("proc.word.sentence_case", "uses", PROC_CAPITALIZE),
    ("input.modality.shift_layer", "complements", PROC_SENTENCE_CASE),
]

BRIDGE_CONCEPTS: list[str] = [
    "input.modality.base_layer",
    "ortho.display.lowercase_register",
    "ortho.display.all_caps",
    "input.modality.caps_latch",
]


def ingest_keyboard_ortho_bridge(
    state: dict,
    *,
    ensure_ortho_bootstrap: bool = True,
    copies: int = 4,
) -> dict[str, Any]:
    """
    Imprint explicit links: Shift → capitalize atom; Caps Lock → ALL CAPS (Upper fold).
    Requires L3; bootstraps Capitalize+Upper if missing.
    """
    state = ensure_prisms(state)
    ortho_rep: dict[str, Any] | None = None
    if ensure_ortho_bootstrap and PROC_CAPITALIZE not in l3_process_ids(state):
        ortho_rep = imprint_capitalize_bootstrap(state, copies=copies)
    if PROC_SENTENCE_CASE not in l3_process_ids(state):
        from casa.prisms.memory.ortho_field_v0 import imprint_process

        imprint_process(state, PROC_SENTENCE_CASE, copies=max(2, copies - 1))

    placed = 0
    for cid in BRIDGE_CONCEPTS:
        imprint_l3_concept(state, cid, copies=max(2, copies - 1))
        placed += 1

    edge_placed = 0
    for src, rel, dst in BRIDGE_EDGES:
        imprint_edge(state, src, rel, dst, copies=copies)
        edge_placed += 1

    state.setdefault("keyboard_ortho_bridge", {})["version"] = "v1"
    state["field_version"] = int(state.get("field_version") or 0) + 1

    edges = l3_process_edges(state)
    hits = sum(1 for e in BRIDGE_EDGES if e in edges)
    return {
        "lattice_id": L3_ID,
        "ortho_bootstrap": ortho_rep,
        "concepts_placed": placed,
        "bridge_edges_placed": edge_placed,
        "bridge_edges_on_field": hits,
        "processes": sorted(l3_process_ids(state)),
        "field_version": state["field_version"],
    }


def bridge_edges_present(state: dict) -> bool:
    edges = set(l3_process_edges(state))
    required = (
        ("input.modality.base_layer", "standard_register", "ortho.display.lowercase_register"),
        ("proc.grapheme.lower", "distinct_from", "ortho.display.lowercase_register"),
        ("input.modality.shift_layer", "surface_effect", PROC_CAPITALIZE),
        ("modifier.caps_lock", "surface_effect", PROC_UPPER),
        ("modifier.caps_lock", "toggles", "input.modality.caps_latch"),
        ("ortho.display.all_caps", "same_as", PROC_UPPER),
    )
    return all(r in edges for r in required)


def main() -> None:
    p = argparse.ArgumentParser(description="Listen keyboard ↔ ortho bridge on L3")
    p.add_argument("--write", action="store_true", help="No-op without --store-dir")
    p.add_argument("--store-dir", type=Path, default=None)
    p.add_argument("--copies", type=int, default=4)
    args = p.parse_args()

    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    rep = ingest_keyboard_ortho_bridge(state, copies=args.copies)
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
