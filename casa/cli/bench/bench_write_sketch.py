#!/usr/bin/env python3
"""Bench write@sketch: связный answer_text (articulation_grammar_v0) без LLM."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
import re
import time
from pathlib import Path


def _normalize_expect(raw: str | list[str] | None) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, str):
        return [raw]
    return list(raw)


def _sentence_count(text: str) -> int:
    return len(re.findall(r"[.!?…]+", text))


def _hit_write(text: str, expect: list[str], *, min_len: int, min_sentences: int) -> bool:
    if len(text.strip()) < min_len:
        return False
    if _sentence_count(text) < min_sentences:
        return False
    blob = text.lower()
    if expect and not any(e.lower() in blob for e in expect):
        return False
    if "понял:" not in blob:
        return False
    return True


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--queries", type=Path, required=True)
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--min-len", type=int, default=80)
    p.add_argument("--min-sentences", type=int, default=2)
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
        expect = _normalize_expect(row.get("expect_any") or row.get("expect_substr"))
        t0 = time.perf_counter()
        _, bundle, decoded, _, _, _ = _run_from_field(
            field_path, store, min_votes=CANONICAL_FIELD_MIN_VOTES
        )
        digest = digest_from_decoded(decoded)
        gated = sn_route(digest, bundle=bundle)
        task = cen_plan(gated, bundle=bundle, user_query=q)
        out = task_to_dict(task)
        ms = (time.perf_counter() - t0) * 1000
        text = str(out.get("answer_text") or "")
        ok = _hit_write(
            text,
            expect,
            min_len=args.min_len,
            min_sentences=args.min_sentences,
        )
        hits += 1 if ok else 0
        results.append({
            "query": q,
            "hit": ok,
            "wall_ms": round(ms, 2),
            "answer_len": len(text),
            "sentences": _sentence_count(text),
            "preview": text[:200],
        })

    report = {
        "store": str(args.store_dir),
        "queries": len(lines),
        "write_at_sketch": hits / len(lines) if lines else 0.0,
        "results": results,
    }
    data = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(data, encoding="utf-8")
    try:
        print(data)
    except UnicodeEncodeError:
        import sys

        sys.stdout.buffer.write(data.encode("utf-8", errors="replace") + b"\n")


if __name__ == "__main__":
    main()
