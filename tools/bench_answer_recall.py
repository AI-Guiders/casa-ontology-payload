#!/usr/bin/env python3
"""Bench answer@k for Russian queries against agent store (--from-field)."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


def _normalize_expect(raw: str | list[str] | None) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, str):
        return [raw]
    return list(raw)


def _hit(blocks: list[dict], expect: list[str]) -> bool:
    blob = " ".join(str(b.get("text", "")) + " " + str(b.get("section", "")) for b in blocks).lower()
    return any(e.lower() in blob for e in expect)


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
    results = []
    hits = 0
    for row in lines:
        q = row["query"]
        expect = _normalize_expect(row.get("expect_substr") or row.get("expect_any"))
        t0 = time.perf_counter()
        _, bundle, decoded, _, _, _ = _run_from_field(
            field_path, store, min_votes=CANONICAL_FIELD_MIN_VOTES
        )
        digest = digest_from_decoded(decoded)
        gated = sn_route(digest, bundle=bundle)
        task = cen_plan(gated, bundle=bundle, user_query=q)
        out = task_to_dict(task)
        ms = (time.perf_counter() - t0) * 1000
        blocks = out.get("answer_blocks") or []
        ok = _hit(blocks, expect) if expect else bool(blocks)
        hits += 1 if ok else 0
        results.append({
            "query": q,
            "hit": ok,
            "wall_ms": round(ms, 2),
            "action": out.get("action"),
            "blocks": len(blocks),
        })

    report = {
        "store": str(args.store_dir),
        "queries": len(lines),
        "answer_at_1": hits / len(lines) if lines else 0.0,
        "results": results,
    }
    data = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(data, encoding="utf-8")
    print(data)


if __name__ == "__main__":
    main()
