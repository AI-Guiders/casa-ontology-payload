#!/usr/bin/env python3
"""Bench input-modality listen: kb bundle concepts on L0_vk_map after core ltm boot."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from boot_core_ltm_v0 import default_core_ltm_dir, merge_core_ltm  # type: ignore
from input_modality_ingest_v0 import default_input_modality_bundle  # type: ignore
from sss_cylinders_v0 import ensure_prisms, memory_lattices  # type: ignore
from sss_stack_v0 import decode_lattice  # type: ignore
from vk_layout_field_v0 import L0_VK_MAP_ID  # type: ignore

REQUIRED_CONCEPTS = (
    "input.device.keyboard",
    "input.modality.physical_key",
    "input.modality.layout",
    "input.modality.shift_layer",
    "input.modality.modifier",
    "input.modality.action_key",
    "input.modality.layout_parity",
    "layout.qwerty_us",
    "layout.jcuken_ru",
    "modifier.shift",
    "action.enter",
    "zone.alphanumeric",
)


def run_bench(state: dict, bundle: dict) -> dict:
    lat = memory_lattices(state).get(L0_VK_MAP_ID) or {}
    dec = decode_lattice(lat, min_votes=1)
    on_field = {str(c.get("concept_id") or "") for c in dec.get("concepts") or []}
    edges = {str(e) for e in dec.get("edges") or []}

    expected = [str(c.get("concept_id") or "") for c in bundle.get("claims") or []]
    missing = [cid for cid in expected if cid not in on_field]

    graph_hits = 0
    graph_total = 0
    for e in (bundle.get("graph") or {}).get("edges") or []:
        src, rel, dst = e.get("src"), e.get("relation"), e.get("dst")
        if not (src and rel and dst):
            continue
        graph_total += 1
        if f"{src}|{rel}|{dst}" in edges:
            graph_hits += 1

    req_missing = [c for c in REQUIRED_CONCEPTS if c not in on_field]
    ok = not missing and not req_missing and graph_hits >= max(1, graph_total // 2)

    return {
        "schema_version": 1,
        "bench": "input_modality_field_v0",
        "bundle_id": bundle.get("bundle_id"),
        "concepts_expected": len(expected),
        "concepts_on_field": len(expected) - len(missing),
        "concepts_missing": missing,
        "required_missing": req_missing,
        "graph_edges_hit": graph_hits,
        "graph_edges_total": graph_total,
        "vk_lattice_edges": len(edges),
        "all_passed": ok,
    }


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Bench input-modality concepts on field")
    p.add_argument("--core-ltm", type=Path, default=default_core_ltm_dir(root=root))
    p.add_argument("--bundle", type=Path, default=default_input_modality_bundle(root=root))
    args = p.parse_args()

    if not (args.core_ltm / "pack.manifest.json").is_file():
        raise SystemExit("core ltm missing — run: python tools/vk_layout_ingest_v0.py")

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    merge_core_ltm(state, args.core_ltm)
    report = run_bench(state, bundle)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(
        f"\nSUMMARY: concepts={report['concepts_on_field']}/{report['concepts_expected']} "
        f"graph={report['graph_edges_hit']}/{report['graph_edges_total']}",
        file=sys.stderr,
    )
    raise SystemExit(0 if report["all_passed"] else 1)


if __name__ == "__main__":
    main()
