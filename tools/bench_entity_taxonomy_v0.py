#!/usr/bin/env python3
"""Bench entity taxonomy: word → entity → instanceOf type."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from entity_hub_ingest_v0 import ingest_entity_hub  # type: ignore
from entity_taxonomy_ingest_v0 import ingest_entity_taxonomy  # type: ignore
from entity_taxonomy_lookup_v0 import entity_type_for_word  # type: ignore
from store_boot_v0 import boot_store  # type: ignore


def run_bench(state: dict, cues: list[dict]) -> dict:
    passed = 0
    rows: list[dict] = []
    for item in cues:
        word = str(item.get("word") or "")
        expect_type = str(item.get("expect_type") or item.get("type_id") or "")
        expect_entity = item.get("expect_entity")
        rep = entity_type_for_word(state, word)
        ok = True
        if expect_type:
            ok = ok and rep.get("type_id") == expect_type
        if expect_entity:
            ok = ok and rep.get("entity_id") == expect_entity
        rows.append({**item, "got": rep, "ok": ok})
        if ok:
            passed += 1
    return {
        "schema_version": 1,
        "bench": "entity_taxonomy_v0",
        "passed": passed,
        "total": len(cues),
        "all_passed": passed == len(cues),
        "items": rows,
    }


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser(description="Bench entity taxonomy on L3")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--hub-bundle", type=Path, default=root / "lab/exp_bilingual_v0/kb-entity-surfaces-dev.v1.json")
    p.add_argument("--taxonomy-bundle", type=Path, default=root / "lab/kb/kb-entity-taxonomy-v1.json")
    p.add_argument("--cues", type=Path, default=root / "lab/kb/entity_taxonomy_eval_cues.v1.json")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    cues = json.loads(args.cues.read_text(encoding="utf-8"))
    t0 = time.perf_counter()
    boot = boot_store(args.store_dir, prefer_field_state=True)
    state = boot["state"]
    ingest_entity_hub(state, json.loads(args.hub_bundle.read_text(encoding="utf-8")))
    ingest_entity_taxonomy(state, json.loads(args.taxonomy_bundle.read_text(encoding="utf-8")))
    boot_ms = round((time.perf_counter() - t0) * 1000)

    report = run_bench(state, cues)
    report["boot_ms"] = boot_ms
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(f"\nSUMMARY: taxonomy {report['passed']}/{report['total']} boot={boot_ms}ms", file=sys.stderr)
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
