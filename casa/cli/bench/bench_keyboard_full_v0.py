#!/usr/bin/env python3
"""Bench full keyboard v1: shift layer, actions, catalog on field."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import sys
from pathlib import Path

from casa.prisms.memory.boot_core_ltm_v0 import default_core_ltm_dir, merge_core_ltm
from casa.prisms.memory.input_modality_ingest_v0 import default_input_modality_bundle
from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms, memory_lattices
from casa.prisms.memory.sss_stack_v0 import decode_lattice
from casa.prisms.memory.vk_decode_v0 import decode_branches, decode_events
from casa.prisms.memory.vk_layout_field_v0 import L0_VK_MAP_ID, compose_index_from_lattice


def run_bench(state: dict, items: list[dict], bundle: dict) -> dict:
    lat = memory_lattices(state).get(L0_VK_MAP_ID) or {}
    dec = decode_lattice(lat, min_votes=1)
    on_field = {str(c.get("concept_id") or "") for c in dec.get("concepts") or []}
    idx = compose_index_from_lattice(lat)
    rows: list[dict] = []
    passed = 0

    for item in items:
        iid = item.get("id")
        ok = True
        detail: dict = {}

        if item.get("events"):
            events = list(item["events"])
            decode = decode_branches(events, state=state)
            exp_layout = item.get("expect_layout") or item.get("expect_winner_layout")
            exp_grapheme = item.get("expect_grapheme")
            exp_contains = item.get("expect_contains")
            if exp_layout and exp_grapheme:
                got = decode.get(exp_layout)
                detail["decode"] = decode
                ok = got == exp_grapheme
            elif exp_layout and exp_contains:
                got = decode.get(exp_layout, "")
                detail["decode"] = decode
                ok = exp_contains in got
            else:
                detail["decode"] = decode

        if exp_concepts := item.get("expect_concepts"):
            missing = [c for c in exp_concepts if c not in on_field]
            detail["concepts_missing"] = missing
            ok = ok and not missing

        if min_keys := item.get("expect_min_physical_keys"):
            pk = int(lat.get("physical_key_count") or 0)
            detail["physical_key_count"] = pk
            ok = ok and pk >= int(min_keys)

        if ok:
            passed += 1
        rows.append({"id": iid, "ok": ok, "detail": detail})

    return {
        "schema_version": 1,
        "bench": "keyboard_full_v1",
        "mapping_count": len(idx),
        "shift_mappings": sum(1 for k in idx if str(k[0]).endswith(".shift")),
        "physical_key_count": int(lat.get("physical_key_count") or 0),
        "role_edges": int(lat.get("role_edge_count") or 0),
        "passed": passed,
        "total": len(rows),
        "all_passed": passed == len(rows),
        "items": rows,
        "bundle_id": bundle.get("bundle_id"),
    }


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Bench full keyboard on CASA field")
    p.add_argument("--core-ltm", type=Path, default=default_core_ltm_dir(root=root))
    p.add_argument("--cues", type=Path, default=root / "lab/exp_bilingual_v0/keyboard_full_cues.v1.json")
    p.add_argument("--bundle", type=Path, default=default_input_modality_bundle(root=root))
    args = p.parse_args()

    if not (args.core_ltm / "pack.manifest.json").is_file():
        raise SystemExit("run: python tools/vk_layout_ingest_v0.py")

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    items = json.loads(args.cues.read_text(encoding="utf-8"))
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    merge_core_ltm(state, args.core_ltm)
    report = run_bench(state, items, bundle)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nSUMMARY: {report['passed']}/{report['total']} keys={report['physical_key_count']}", file=sys.stderr)
    raise SystemExit(0 if report["all_passed"] else 1)


if __name__ == "__main__":
    main()
