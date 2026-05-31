#!/usr/bin/env python3
"""Bench POS claims on L3: word → has_pos → pos.*."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import sys
import time
from pathlib import Path

from casa.prisms.memory.pos_claims_ingest_v0 import ingest_pos_claims
from casa.prisms.memory.pos_lookup_v0 import word_pos
from casa.prisms.shared.store_boot_v0 import boot_store


def run_bench(state: dict, cues: list[dict]) -> dict:
    passed = 0
    rows: list[dict] = []
    for item in cues:
        word = str(item.get("word") or item.get("lemma") or "")
        expect = str(item.get("expect_pos") or item.get("pos_id") or "")
        if expect and not expect.startswith("pos."):
            expect = f"pos.{expect.lower()}"
        rep = word_pos(state, word)
        got = rep.get("pos")
        ok = bool(expect) and got == expect
        rows.append({"id": item.get("id"), "word": word, "expect": expect, "got": got, "ok": ok})
        if ok:
            passed += 1
    return {
        "schema_version": 1,
        "bench": "pos_claims_v0",
        "passed": passed,
        "total": len(cues),
        "all_passed": passed == len(cues),
        "items": rows,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Bench POS claims on L3")
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--cues", type=Path, default=None, help="JSON array; default = all bundle claims")
    p.add_argument("--max-cues", type=int, default=0, help="Limit cues from bundle (0=all)")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    if args.cues:
        cues = json.loads(args.cues.read_text(encoding="utf-8"))
    else:
        cues = [
            {
                "id": f"pos_{i}",
                "word": row.get("lemma") or row.get("word"),
                "expect_pos": row.get("pos_id") or row.get("pos"),
            }
            for i, row in enumerate(bundle.get("claims") or [])
        ]

    if args.max_cues and len(cues) > args.max_cues:
        cues = cues[: args.max_cues]

    t0 = time.perf_counter()
    boot = boot_store(args.store_dir, prefer_field_state=True)
    state = boot["state"]
    ingest_pos_claims(state, bundle, copies=4)
    boot_ms = round((time.perf_counter() - t0) * 1000)

    report = run_bench(state, cues)
    report["boot_ms"] = boot_ms
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    print(
        f"\nSUMMARY: pos {report['passed']}/{report['total']} boot={boot_ms}ms",
        file=sys.stderr,
    )
    raise SystemExit(0 if report["all_passed"] else 1)


if __name__ == "__main__":
    main()
