#!/usr/bin/env python3
"""Block 9b: passage comprehension — SVR C, duck-test reply (text tract, no oracle)."""

from __future__ import annotations

import json
from pathlib import Path

from probe_infra import default_store, finalize_honest_probe_report, generated_report_path, setup_probe_imports

_REPO = Path(__file__).resolve().parents[2]
_PILOT = _REPO / "lessons" / "ru-text-tract" / "data" / "passage-comprehend-pilot-v1.json"
_PROBE = "probe_passage_comprehend_ru_v0"


def _load_cases(path: Path | None = None) -> list[dict]:
    p = path or _PILOT
    data = json.loads(p.read_text(encoding="utf-8"))
    return [c for c in (data.get("cases") or []) if isinstance(c, dict)]


def _run(*, store_id: str = "von-neumann", cases: list[dict] | None = None) -> dict:
    setup_probe_imports()
    from casa.domain.subject_articulation import compose_subject_utterance
    from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
    from casa.prisms.control.fpn_state import WorkingMemory
    from casa.prisms.shared.store_bundles import load_store_bundles
    from casa.prisms.shared.store_lock import store_session_lock
    from casa.prisms.tick.semantic_read import classify_query_intent

    cases = cases or _load_cases()
    store = default_store(store_id)
    items: list[dict] = []
    know = 0

    with store_session_lock(store, holder=f"probe:{_PROBE}"):
        from casa.cli.ingest_state import resolve_ingest_state

        state = resolve_ingest_state(store, None)
        bundle = load_store_bundles(store)
        wm = WorkingMemory()

        for case in cases:
            passage = str(case.get("passage") or "").strip()
            query = str(case.get("query") or "").strip()
            combined = f"{passage}\n\n{query}" if passage else query
            intent = classify_query_intent(combined)
            ctx = gather_subject_dialogue_blocks(combined, None, state, wm, store, bundle=bundle)
            reply = compose_subject_utterance(combined, ctx).lower()
            top_cids = [str(b.get("concept_id") or "") for b in ctx.blocks[:6]]
            prefix = str(case.get("expect_concept_prefix") or "")
            cid_ok = any(c.startswith(prefix) for c in top_cids if c) if prefix else bool(top_cids)
            expect_tokens = [str(t).lower() for t in (case.get("expect_in_reply") or [])]
            text_ok = all(tok in reply for tok in expect_tokens) if expect_tokens else bool(reply.strip())
            verdict = "know" if text_ok else "wrong"
            if verdict == "know":
                know += 1
            items.append(
                {
                    "case_id": case.get("case_id"),
                    "query": query,
                    "passage_excerpt": passage[:120],
                    "verdict": verdict,
                    "intent": intent,
                    "top_concepts": top_cids,
                    "reply_excerpt": reply[:200],
                    "cid_ok": cid_ok,
                    "text_ok": text_ok,
                }
            )

        report = {
            "store_id": store.name,
            "probe": _PROBE,
            "total": len(items),
            "know": know,
            "wrong": len(items) - know,
            "empty": 0,
            "ambiguous": 0,
            "items": items,
        }
        report = finalize_honest_probe_report(state, report, store=store, probe_id=_PROBE)

    path = generated_report_path("teacher-probe-passage-comprehend-ru-v0.json")
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"probe": _PROBE, "know": know, "total": len(items), "path": str(path)}, ensure_ascii=False))
    return report


def main() -> None:
    report = _run()
    raise SystemExit(0 if report.get("know") == report.get("total") and report.get("total") else 1)


if __name__ == "__main__":
    main()
