#!/usr/bin/env python3
"""List E: edges from vis frame cues to math.* (probe diagnostics)."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.cli.ingest_state import resolve_ingest_state
from casa.domain.visual_tract import LATTICE_V1_LUM, PREFIX_VIS_LUM
from casa.domain.prism_ids import PRISM_VISUAL
from casa.domain.prism_wire import prism_block
from casa.prisms.memory.f0_stack import decode_f0_lattice
from casa.prisms.memory.memory_prisms import memory_lattices
from casa.prisms.shared.store_lock import store_session_lock
from casa.prisms.visual.bootstrap import ensure_prism_visual
from casa.prisms.visual.bridge_math import predict_math_for_vis_cue, vis_frame_concept_id

SET_CONCEPTS = (
    "math.set.intersect",
    "math.set.union",
    "math.set.subset",
    "math.set.disjoint",
    "math.set.difference",
)

REGION_FRAMES = (
    "venn-region-intersect",
    "venn-region-union",
    "venn-region-subset",
    "venn-region-disjoint",
    "venn-region-a-only",
)


def _collect_edges(state: dict) -> dict[str, dict[str, int]]:
    """vis_cid -> {math_cid: count} from lum cells + schema-math decode."""
    ensure_prism_visual(state)
    out: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    lum = (prism_block(state, PRISM_VISUAL).get("lattices") or {}).get(LATTICE_V1_LUM) or {}
    prefix_vis = PREFIX_VIS_LUM + "frame."

    for cell in lum.get("cells") or []:
        if not isinstance(cell, list):
            continue
        for tok in cell:
            if not isinstance(tok, str) or not tok.startswith("E:"):
                continue
            parts = tok.split("|", 2)
            if len(parts) != 3 or not parts[2].startswith("math."):
                continue
            src, _, dst = parts
            if not src.startswith(prefix_vis):
                continue
            out[src][dst] += 1

    math_lat = memory_lattices(state).get("schema-math") or {}
    if math_lat.get("cells"):
        dec = decode_f0_lattice(math_lat)
        for es in dec.get("edges") or []:
            if not isinstance(es, str) or not es.startswith("E:"):
                continue
            parts = es.split("|", 2)
            if len(parts) != 3 or not parts[2].startswith("math."):
                continue
            src, _, dst = parts
            if src.startswith(prefix_vis):
                out[src][dst] += 2

    return out


def main() -> None:
    store = (_REPO / "agents" / "von-neumann").resolve()
    with store_session_lock(store, holder="inspect:vis-math-edges"):
        state = resolve_ingest_state(store, None)
        edges = _collect_edges(state)

    report: dict = {"region_frames": {}, "set_totals_from_region": defaultdict(int)}
    for fid in REGION_FRAMES:
        vis = vis_frame_concept_id(fid)
        row = dict(edges.get(vis, {}))
        set_only = {k: v for k, v in row.items() if k in SET_CONCEPTS}
        preds = predict_math_for_vis_cue(state, fid, top_k=10)
        report["region_frames"][fid] = {
            "edges_to_set": set_only,
            "edge_count_set": sum(set_only.values()),
            "all_math_edges": dict(sorted(row.items(), key=lambda x: (-x[1], x[0]))[:12]),
            "predict_top": preds[:8],
        }
        for k, v in set_only.items():
            report["set_totals_from_region"][k] += v

    report["set_totals_from_region"] = dict(report["set_totals_from_region"])
    out = _REPO / "lab/visual-curriculum/generated/inspect-venn-region-edges.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
