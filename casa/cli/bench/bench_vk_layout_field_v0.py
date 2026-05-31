#!/usr/bin/env python3
"""Bench VK decode: JSON oracle vs L0_vk_map field memory."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import sys
from pathlib import Path

from casa.prisms.memory.boot_core_ltm_v0 import default_core_ltm_dir, merge_core_ltm
from casa.prisms.memory.sss_cylinders_v0 import ensure_prisms
from casa.prisms.memory.vk_decode_v0 import _json_index, decode_branches, resolve_decode_index
from casa.prisms.memory.vk_layout_field_v0 import compose_index_from_state


def run_bench(state: dict, items: list[dict]) -> dict:
    json_idx = _json_index()
    field_idx = compose_index_from_state(state) or {}
    rows: list[dict] = []
    passed = 0

    for item in items:
        events = list(item.get("events") or [])
        json_dec = decode_branches(events, vk_index=json_idx)
        field_dec = decode_branches(events, state=state)
        idx_match = json_dec == field_dec
        exp = item.get("expect_branches") or {}
        if not exp:
            layout = item.get("expect_winner_layout")
            grapheme = item.get("expect_grapheme")
            if layout and grapheme:
                exp = {layout: grapheme}
        expect_ok = all(field_dec.get(k) == v for k, v in exp.items()) if exp else True
        ok = idx_match and expect_ok
        if ok:
            passed += 1
        rows.append(
            {
                "id": item.get("id"),
                "json_decode": json_dec,
                "field_decode": field_dec,
                "index_match": idx_match,
                "expect_ok": expect_ok,
                "ok": ok,
            }
        )

    return {
        "schema_version": 1,
        "bench": "vk_layout_field_v0",
        "field_mapping_count": len(field_idx),
        "json_mapping_count": len(json_idx),
        "index_equal": json_idx == field_idx,
        "passed": passed,
        "total": len(rows),
        "all_passed": passed == len(rows),
        "items": rows,
    }


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Bench VK field memory vs JSON oracle")
    p.add_argument(
        "--cues",
        type=Path,
        default=root / "lab/exp_bilingual_v0/layout_parity_cues.v1.json",
    )
    p.add_argument(
        "--core-ltm",
        type=Path,
        default=default_core_ltm_dir(root=root),
    )
    args = p.parse_args()

    if not (args.core_ltm / "pack.manifest.json").is_file():
        raise SystemExit(f"core ltm missing — run: python tools/vk_layout_ingest_v0.py")

    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    boot = merge_core_ltm(state, args.core_ltm)
    items = json.loads(args.cues.read_text(encoding="utf-8"))
    report = run_bench(state, items)
    report["boot"] = boot
    field_idx = compose_index_from_state(state) or {}
    _, src = resolve_decode_index(state=state)
    report["decode_source"] = src
    report["compose_edges"] = len(field_idx)

    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    print(f"\nSUMMARY: {report['passed']}/{report['total']} field={report['field_mapping_count']}", file=sys.stderr)
    raise SystemExit(0 if report["all_passed"] else 1)


if __name__ == "__main__":
    main()
