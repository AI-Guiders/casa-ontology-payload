#!/usr/bin/env python3
"""Oral exam: run queries, score by category, write human-readable report."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path


def _code_leak(text: str) -> bool:
    t = text.lower()
    if "по памяти:" not in t:
        return False
    return any(x in t for x in ("readline", "console.write", "tryparse", "два целых с ввода"))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--queries", type=Path, required=True)
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    from canonical import CANONICAL_FIELD_MIN_VOTES  # type: ignore
    from sn_cen_infer import _run_from_field  # type: ignore
    from sn_cen_runtime import cen_plan, digest_from_decoded, sn_route, task_to_dict  # type: ignore

    store = args.store_dir.resolve()
    field_path = store / "field_state.json"
    lines = [json.loads(x) for x in args.queries.read_text(encoding="utf-8").splitlines() if x.strip()]

    by_cat: dict[str, list[dict]] = defaultdict(list)
    results: list[dict] = []
    hits = 0

    for row in lines:
        q = row["query"]
        cat = row.get("category", "other")
        expect_action = row.get("expect_action")
        expect_any = row.get("expect_any") or []

        t0 = time.perf_counter()
        _, bundle, decoded, _, _, _ = _run_from_field(
            field_path, store, min_votes=CANONICAL_FIELD_MIN_VOTES
        )
        gated = sn_route(digest_from_decoded(decoded), bundle=bundle)
        out = task_to_dict(cen_plan(gated, bundle=bundle, user_query=q))
        ms = (time.perf_counter() - t0) * 1000

        text = out.get("answer_text") or ""
        blob = text.lower()
        ok = True
        notes: list[str] = []

        if expect_action and out.get("action") != expect_action:
            ok = False
            notes.append(f"action={out.get('action')}, want {expect_action}")
        if expect_any and not any(e.lower() in blob for e in expect_any):
            ok = False
            notes.append("missing expect_any")
        if expect_action == "no_memory" and _code_leak(text):
            ok = False
            notes.append("code leak in По памяти")
        if cat == "off_topic" and out.get("action") != "no_memory":
            ok = False
            notes.append("off_topic should be no_memory")

        hits += 1 if ok else 0
        entry = {
            "category": cat,
            "query": q,
            "hit": ok,
            "action": out.get("action"),
            "wall_ms": round(ms, 2),
            "answer_text": text,
            "notes": notes,
        }
        results.append(entry)
        by_cat[cat].append(entry)

    cat_scores = {
        c: sum(1 for r in rs if r["hit"]) / len(rs) if rs else 0.0 for c, rs in by_cat.items()
    }

    report = {
        "store": str(args.store_dir),
        "queries": len(lines),
        "oral_pass_rate": hits / len(lines) if lines else 0.0,
        "by_category": cat_scores,
        "results": results,
    }
    data = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(data, encoding="utf-8")
    print(data)


if __name__ == "__main__":
    main()
