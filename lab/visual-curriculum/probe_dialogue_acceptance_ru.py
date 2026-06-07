#!/usr/bin/env python3
"""Block 12 gate — ADR-0049 dialogue acceptance (text tract, field-realize)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from probe_infra import default_store, finalize_honest_probe_report, generated_report_path, setup_probe_imports

_PLAN = (
    Path(__file__).resolve().parents[2]
    / "lessons/ru-text-tract/data/dialog-moment-plan-v1.json"
)
_PROBE = "probe_dialogue_acceptance_ru"


def _scenario_pass(case: dict[str, Any], *, reply: str, top_cids: list[str]) -> tuple[bool, dict[str, Any]]:
    reply_l = reply.lower()
    detail: dict[str, Any] = {"scenario_id": case.get("scenario_id")}
    if case.get("expect_honest_partial"):
        ok = any(
            tok in reply_l
            for tok in ("частично", "не уверен", "не знаю", "kb", "journal", "field", "defer", "partial")
        )
        detail["honest_partial"] = ok
        return ok, detail
    if expect_any := case.get("expect_concept_any"):
        cid_ok = any(str(c) in top_cids for c in expect_any)
        text_tokens = [str(t).lower() for t in (case.get("expect_in_reply") or [])]
        text_ok = all(t in reply_l for t in text_tokens) if text_tokens else True
        ok = cid_ok or text_ok
        detail.update(
            {
                "cid_ok": cid_ok,
                "text_ok": text_ok,
                "expect_concept_any": expect_any,
                "expect_in_reply": text_tokens or None,
            }
        )
        return ok, detail
    if expect_in := case.get("expect_in_reply"):
        tokens = [str(t).lower() for t in expect_in]
        ok = all(t in reply_l for t in tokens)
        detail["expect_in_reply"] = tokens
        return ok, detail
    return False, detail


def main() -> None:
    setup_probe_imports()
    from casa.domain.subject_articulation import compose_subject_utterance
    from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
    from casa.prisms.control.fpn_state import WorkingMemory
    from casa.prisms.shared.store_bundles import load_store_bundles
    from casa.prisms.shared.store_lock import store_session_lock

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--plan", type=Path, default=_PLAN)
    args = p.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    scenarios = list(plan.get("scenarios") or [])
    store = default_store(args.store)
    items: list[dict] = []
    know = 0

    with store_session_lock(store, holder=f"probe:{_PROBE}"):
        from casa.cli.ingest_state import resolve_ingest_state

        state = resolve_ingest_state(store, None)
        bundle = load_store_bundles(store)
        wm = WorkingMemory()
        for case in scenarios:
            q = str(case.get("query") or "")
            ctx = gather_subject_dialogue_blocks(q, None, state, wm, store, bundle=bundle)
            reply = compose_subject_utterance(q, ctx)
            top_cids = [str(b.get("concept_id") or "") for b in ctx.blocks[:6]]
            ok, detail = _scenario_pass(case, reply=reply, top_cids=top_cids)
            if ok:
                know += 1
            items.append(
                {
                    "query": q,
                    "verdict": "know" if ok else "wrong",
                    "top_concepts": top_cids,
                    "reply_excerpt": reply[:200],
                    **detail,
                }
            )
        report: dict[str, Any] = {
            "store_id": store.name,
            "probe": _PROBE,
            "plan": str(args.plan),
            "total": len(items),
            "know": know,
            "wrong": len(items) - know,
            "items": items,
            "gate_pass": know == len(items) and bool(items),
        }
        report = finalize_honest_probe_report(state, report, store=store, probe_id=_PROBE)

    out = generated_report_path("teacher-probe-dialogue-acceptance-ru.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "probe": _PROBE,
                "know": know,
                "total": len(items),
                "gate_pass": report.get("gate_pass"),
                "path": str(out),
            },
            ensure_ascii=False,
        )
    )
    raise SystemExit(0 if report.get("gate_pass") else 1)


if __name__ == "__main__":
    main()
