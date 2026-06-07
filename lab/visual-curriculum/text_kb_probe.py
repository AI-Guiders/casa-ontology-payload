#!/usr/bin/env python3
"""Shared text-tract KB bind probe runner (ortho / punct)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from probe_infra import default_store, finalize_honest_probe_report, generated_report_path, setup_probe_imports


def _cases_from_plan(plan_path: Path) -> tuple[dict[str, Any], ...]:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    raw = plan.get("cases") or plan.get("scenarios") or []
    out: list[dict[str, Any]] = []
    for row in raw:
        if row.get("wired") is False:
            continue
        q = str(row.get("query") or "")
        if not q:
            continue
        expect_cid = row.get("expect_cid_prefix") or row.get("expect_cid")
        expect_reply = row.get("expect_in_reply") or row.get("expect_semantic") or []
        out.append(
            {
                "case_id": row.get("case_id") or row.get("scenario_id"),
                "query": q,
                "expect_cid_prefix": str(expect_cid or ""),
                "expect_in_reply": tuple(str(x) for x in expect_reply),
            }
        )
    return tuple(out)


def run_text_kb_probe(
    *,
    probe_id: str,
    plan_path: Path,
    report_filename: str,
    store_id: str = "von-neumann",
) -> dict[str, Any]:
    setup_probe_imports()
    from casa.domain.subject_articulation import compose_subject_utterance
    from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
    from casa.prisms.control.fpn_state import WorkingMemory
    from casa.prisms.shared.store_bundles import load_store_bundles
    from casa.prisms.shared.store_lock import store_session_lock

    cases = _cases_from_plan(plan_path)
    store = default_store(store_id)
    items: list[dict[str, Any]] = []
    know = 0

    with store_session_lock(store, holder=f"probe:{probe_id}"):
        from casa.cli.ingest_state import resolve_ingest_state

        state = resolve_ingest_state(store, None)
        bundle = load_store_bundles(store)
        wm = WorkingMemory()

        for case in cases:
            q = str(case["query"])
            ctx = gather_subject_dialogue_blocks(q, None, state, wm, store, bundle=bundle)
            reply = compose_subject_utterance(q, ctx).lower()
            top_cids = [str(b.get("concept_id") or "") for b in ctx.blocks[:6]]
            prefix = str(case.get("expect_cid_prefix") or "")
            cid_ok = any(c.startswith(prefix) for c in top_cids if c) if prefix else True
            expect = case.get("expect_in_reply") or ()
            text_ok = all(str(tok).lower() in reply for tok in expect) if expect else bool(reply.strip())
            verdict = "know" if cid_ok and text_ok else "wrong"
            if verdict == "know":
                know += 1
            items.append(
                {
                    "case_id": case.get("case_id"),
                    "query": q,
                    "verdict": verdict,
                    "resolved_skill": ctx.resolved_skill,
                    "top_concepts": top_cids,
                    "reply_excerpt": reply[:200],
                    "cid_ok": cid_ok,
                    "text_ok": text_ok,
                }
            )

        total = len(items)
        report: dict[str, Any] = {
            "store_id": store.name,
            "probe": probe_id,
            "plan": str(plan_path),
            "total": total,
            "know": know,
            "wrong": total - know,
            "empty": 0,
            "ambiguous": 0,
            "items": items,
            "gate_pass": total > 0 and know == total,
        }
        report = finalize_honest_probe_report(state, report, store=store, probe_id=probe_id)

    path = generated_report_path(report_filename)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"probe": probe_id, "gate_pass": report.get("gate_pass"), "know": know, "total": total, "path": str(path)},
            ensure_ascii=False,
        )
    )
    return report
