#!/usr/bin/env python3
"""Write hot path lab: SN/CEN when KB present, else phrase articulation (step 3)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_vc = Path(__file__).resolve().parent
if str(_vc) not in sys.path:
    sys.path.insert(0, str(_vc))
from vc_paths import install  # noqa: E402

install(__file__)


def _normalize_expect(raw: str | list[str] | None) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, str):
        return [raw]
    return list(raw)


def _hit(text: str, expect: list[str]) -> bool:
    blob = text.lower()
    if "понял:" not in blob:
        return False
    return not expect or any(e.lower() in blob for e in expect)


def _store_has_kb_field_bundle(store_dir: Path) -> bool:
    from casa.prisms.shared.field_write import bundle_from_field_state, load_field_state

    state = load_field_state(store_dir / "field_state.json", store_dir=store_dir)
    try:
        bundle_from_field_state(state, store_dir=store_dir)
        return True
    except (ValueError, FileNotFoundError):
        return False


def _sn_cen_write(store_dir: Path, query: str) -> dict:
    from casa.prisms.shared.canonical import CANONICAL_FIELD_MIN_VOTES
    from casa.prisms.control.sn_cen_infer import _run_from_field
    from casa.prisms.control.sn_cen_runtime import cen_plan, digest_from_decoded, sn_route, task_to_dict
    from casa.prisms.tick.articulation_realize import compose_answer_text

    field_path = store_dir / "field_state.json"
    t0 = time.perf_counter()
    _, bundle, decoded, _, _, _ = _run_from_field(field_path, store_dir, min_votes=CANONICAL_FIELD_MIN_VOTES)
    gated = sn_route(digest_from_decoded(decoded), bundle=bundle)
    task = cen_plan(gated, bundle=bundle, user_query=query)
    out = task_to_dict(task)
    blocks = out.get("answer_blocks") or []
    text = str(out.get("answer_text") or "") or compose_answer_text(query, blocks, action=out.get("action", ""))
    return {
        "backend": "sn_cen",
        "text": text,
        "wall_ms": round((time.perf_counter() - t0) * 1000, 2),
        "blocks": len(blocks),
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
        expect = _normalize_expect(row.get("expect_any"))
        t0 = time.perf_counter()
        if has_kb:
            rep = _sn_cen_write(store, q)
            backend = rep["backend"]
            text = rep["text"]
        else:
            from casa.prisms.tick.articulation_phrase_write import phrase_write_from_query

            rep = phrase_write_from_query(q)
            backend = "phrase_event"
            text = str(rep.get("answer_text") or "")
            rep = {"event_id": rep.get("event_id"), "wall_ms": round((time.perf_counter() - t0) * 1000, 2)}
        ok = _hit(text, expect)
        hits += 1 if ok else 0
        results.append({
            "query": q,
            "hit": ok,
            "backend": backend,
            "preview": text[:220],
            **rep,
        })

    report = {
        "store": str(store),
        "has_kb_bundle": has_kb,
        "write_at_1": hits / len(lines) if lines else 0.0,
        "results": results,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    out = args.out or (_vc / "generated" / "bench-write-hot-path.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")
    print(text)
    raise SystemExit(0 if hits == len(lines) else 1)


if __name__ == "__main__":
    main()
