#!/usr/bin/env python3
"""Bench realize v0: lower paste_ratio vs sketch; answer still hits expect."""

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
    p.add_argument("--max-paste-ratio", type=float, default=0.45)
    args = p.parse_args()

    from articulation_grammar_v0 import compose_answer_text_sketch  # type: ignore
    from articulation_realize_v0 import compose_answer_text, paste_ratio  # type: ignore
    from canonical import CANONICAL_FIELD_MIN_VOTES  # type: ignore
    from sn_cen_infer import _run_from_field  # type: ignore
    from sn_cen_runtime import cen_plan, digest_from_decoded, sn_route, task_to_dict  # type: ignore

    def _normalize_expect(raw: str | list[str] | None) -> list[str]:
        if not raw:
            return []
        if isinstance(raw, str):
            return [raw]
        return list(raw)

    def _hit_text(text: str, expect: list[str]) -> bool:
        blob = text.lower()
        return not expect or any(e.lower() in blob for e in expect)

    def _hit_blocks(blocks: list, expect: list[str]) -> bool:
        blob = " ".join(str(b.get("text", "")) for b in blocks).lower()
        return _hit_text(blob, expect)

    store = args.store_dir.resolve()
    field_path = store / "field_state.json"
    lines = [json.loads(x) for x in args.queries.read_text(encoding="utf-8").splitlines() if x.strip()]
    results = []
    ok = 0
    for row in lines:
        q = row["query"]
        expect = _normalize_expect(row.get("expect_any") or row.get("expect_substr"))
        t0 = time.perf_counter()
        _, bundle, decoded, _, _, _ = _run_from_field(
            field_path, store, min_votes=CANONICAL_FIELD_MIN_VOTES
        )
        gated = sn_route(digest_from_decoded(decoded), bundle=bundle)
        task = cen_plan(gated, bundle=bundle, user_query=q)
        out = task_to_dict(task)
        ms = (time.perf_counter() - t0) * 1000
        blocks = out.get("answer_blocks") or []
        realize_text = str(out.get("answer_text") or "")
        sketch_text = compose_answer_text_sketch(q, blocks, action=out.get("action", ""))
        pr = paste_ratio(realize_text, blocks)
        block_hit = _hit_blocks(blocks, expect)
        text_hit = _hit_text(realize_text, expect)
        realize_hit = text_hit and pr <= args.max_paste_ratio
        if realize_hit:
            ok += 1
        results.append({
            "query": q,
            "hit": realize_hit,
            "block_hit": block_hit,
            "text_hit": text_hit,
            "paste_ratio": round(pr, 3),
            "paste_ok": pr <= args.max_paste_ratio,
            "wall_ms": round(ms, 2),
            "realize_preview": realize_text[:220],
            "sketch_preview": sketch_text[:120],
        })

    report = {
        "store": str(args.store_dir),
        "queries": len(lines),
        "realize_pass": ok / len(lines) if lines else 0.0,
        "max_paste_ratio": args.max_paste_ratio,
        "results": results,
    }
    data = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(data, encoding="utf-8")
    print(data)


if __name__ == "__main__":
    main()
