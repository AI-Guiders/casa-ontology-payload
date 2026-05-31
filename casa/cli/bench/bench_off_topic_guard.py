#!/usr/bin/env python3
"""Bench off-topic guard: no C# answers on chitchat / weak match."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import time
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--queries", type=Path, required=True)
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    from casa.prisms.shared.canonical import CANONICAL_FIELD_MIN_VOTES
    from casa.prisms.control.sn_cen_infer import _run_from_field
    from casa.prisms.control.sn_cen_runtime import cen_plan, digest_from_decoded, sn_route, task_to_dict

    store = args.store_dir.resolve()
    field_path = store / "field_state.json"
    lines = [json.loads(x) for x in args.queries.read_text(encoding="utf-8").splitlines() if x.strip()]
    results = []
    hits = 0
    for row in lines:
        q = row["query"]
        expect_action = row.get("expect_action")
        expect_any = row.get("expect_any") or []
        forbid = row.get("forbid") or []
        t0 = time.perf_counter()
        _, bundle, decoded, _, _, _ = _run_from_field(
            field_path, store, min_votes=CANONICAL_FIELD_MIN_VOTES
        )
        gated = sn_route(digest_from_decoded(decoded), bundle=bundle)
        out = task_to_dict(cen_plan(gated, bundle=bundle, user_query=q))
        ms = (time.perf_counter() - t0) * 1000
        text = (out.get("answer_text") or "").lower()
        ok = True
        if expect_action:
            allowed = {expect_action, "open_kb", "answer_from_memory"}
            if out.get("action") not in allowed:
                ok = False
        if expect_any and not any(e.lower() in text for e in expect_any):
            ok = False
        for bad in forbid:
            bl = bad.lower()
            if bl in text and not any(
                x in text for x in (f"не отвечай", f"не {bl}", "не уроком", "не диалог")
            ):
                ok = False
        if expect_action == "no_memory" and "по памяти:" in text:
            if any(x in text for x in ("readline", "console.write", "tryparse", "два целых с ввода")):
                ok = False
        hits += 1 if ok else 0
        results.append(
            {
                "query": q,
                "hit": ok,
                "action": out.get("action"),
                "wall_ms": round(ms, 2),
                "preview": (out.get("answer_text") or "")[:180],
            }
        )

    report = {
        "store": str(args.store_dir),
        "queries": len(lines),
        "guard_at_1": hits / len(lines) if lines else 0.0,
        "results": results,
    }
    data = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(data, encoding="utf-8")
    print(data)


if __name__ == "__main__":
    main()
