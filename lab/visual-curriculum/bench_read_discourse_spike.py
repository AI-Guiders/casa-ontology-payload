#!/usr/bin/env python3
"""Discourse read spike — honest gap report for canon/KB on literacy store (step 5)."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

_vc = Path(__file__).resolve().parent
if str(_vc) not in sys.path:
    sys.path.insert(0, str(_vc))
from vc_paths import install  # noqa: E402

install(__file__)


def _tokens(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[\w\u0400-\u04FF]+", text, flags=re.UNICODE) if len(w) >= 3}


def _hit(blob: str, expect: list[str], *, query: str = "") -> bool:
    b = blob.lower()
    q = query.lower()
    # Do not count expect tokens that appear only in the echoed query prefix.
    for e in expect:
        needle = e.lower()
        if needle not in b:
            continue
        if q and needle in q and b.count(needle) <= q.count(needle):
            continue
        return True
    return not expect and bool(b.strip())


def _semantic_hit(row: dict, channels: dict) -> bool:
    """True only when retrieval/content matches expect — not query echo."""
    if row.get("kind") == "pilot_phrase":
        return bool((channels.get("phrase_event") or {}).get("hit"))
    q = str(row["query"])
    expect = list(row.get("expect_any") or [])
    if (channels.get("sn_cen") or {}).get("hit"):
        return True
    if row.get("definition"):
        return False
    pe = channels.get("phrase_event") or {}
    return _hit(str(pe.get("preview") or ""), expect, query=q)


def _store_has_kb_field_bundle(store_dir: Path) -> bool:
    from casa.prisms.shared.field_write import bundle_from_field_state, load_field_state

    state = load_field_state(store_dir / "field_state.json", store_dir=store_dir)
    try:
        bundle_from_field_state(state, store_dir=store_dir)
        return True
    except (ValueError, FileNotFoundError):
        return False


def _sn_cen_read(store_dir: Path, query: str) -> dict:
    from casa.prisms.shared.canonical import CANONICAL_FIELD_MIN_VOTES
    from casa.prisms.control.sn_cen_infer import _run_from_field
    from casa.prisms.control.sn_cen_runtime import cen_plan, digest_from_decoded, sn_route, task_to_dict

    field_path = store_dir / "field_state.json"
    t0 = time.perf_counter()
    _, bundle, decoded, _, _, _ = _run_from_field(field_path, store_dir, min_votes=CANONICAL_FIELD_MIN_VOTES)
    gated = sn_route(digest_from_decoded(decoded), bundle=bundle)
    task = cen_plan(gated, bundle=bundle, user_query=query)
    out = task_to_dict(task)
    blocks = out.get("answer_blocks") or []
    blob = " ".join(str(b.get("text", "")) for b in blocks)
    return {
        "path": "sn_cen",
        "hit": _hit(blob, []),
        "blocks": len(blocks),
        "action": out.get("action"),
        "preview": blob[:240],
        "wall_ms": round((time.perf_counter() - t0) * 1000, 2),
    }


def _predict_read(store_dir: Path, query: str) -> dict:
    from casa.cli.ingest_state import resolve_ingest_state
    from casa.prisms.tick.predict_tick import predict_tick

    state = resolve_ingest_state(store_dir, None)
    t0 = time.perf_counter()
    tick = predict_tick(state, query, modality="t9", top_k=8)
    hyp = (tick.get("predict") or {}).get("hypothesis") or ""
    return {
        "path": "predict_t9",
        "verdict": tick.get("verdict"),
        "hypothesis": hyp[:120] if hyp else "",
        "wall_ms": round((time.perf_counter() - t0) * 1000, 2),
    }


def _phrase_event_read(query: str, expect: list[str]) -> dict:
    from casa.prisms.tick.articulation_phrase_write import phrase_write_from_query

    row = phrase_write_from_query(query)
    text = str(row.get("answer_text") or "")
    return {
        "path": "phrase_event",
        "hit": _hit(text, expect, query=query),
        "event_id": row.get("event_id"),
        "preview": text[:240],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--queries", type=Path, required=True)
    p.add_argument("--store-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    store = args.store_dir.resolve()
    has_kb = _store_has_kb_field_bundle(store)
    lines = [json.loads(x) for x in args.queries.read_text(encoding="utf-8").splitlines() if x.strip()]
    results = []
    hits = 0
    for row in lines:
        q = str(row["query"])
        expect = list(row.get("expect_any") or [])
        channels: dict = {"has_kb_bundle": has_kb}
        if has_kb:
            sn = _sn_cen_read(store, q)
            sn["hit"] = _hit(sn.get("preview", ""), expect, query=q)
            channels["sn_cen"] = sn
        else:
            channels["sn_cen"] = {"path": "sn_cen", "skipped": True, "reason": "no_kb_bundle"}
        channels["predict"] = _predict_read(store, q)
        pe = _phrase_event_read(q, expect)
        channels["phrase_event"] = pe
        semantic = _semantic_hit(row, channels)
        phrase_only = bool(pe.get("hit")) and not row.get("definition")
        best_hit = semantic or phrase_only
        if best_hit:
            hits += 1
        gap = "none" if semantic else (
            "phrase_collision_only" if phrase_only and row.get("definition") else (
                "needs_kb_ingest" if row.get("definition") else (
                    "weak_retrieval" if not best_hit else "phrase_pilot_ok"
                )
            )
        )
        results.append({
            "query": q,
            "definition": row.get("definition"),
            "expect_any": expect,
            "hit": best_hit,
            "semantic_hit": semantic,
            "phrase_hit": pe.get("hit"),
            "gap": gap,
            "channels": channels,
        })

    report = {
        "store": str(store),
        "has_kb_bundle": has_kb,
        "queries": len(lines),
        "read_at_1": hits / len(lines) if lines else 0.0,
        "semantic_at_1": sum(1 for r in results if r.get("semantic_hit")) / len(lines) if lines else 0.0,
        "results": results,
        "verdict": (
            "needs_kb_ingest"
            if not has_kb and sum(1 for r in results if r.get("semantic_hit")) == 0
            else ("mixed" if hits else "miss")
        ),
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    out = args.out or (_vc / "generated" / "bench-read-discourse-spike.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    print(text)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
