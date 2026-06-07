#!/usr/bin/env python3
"""RU-N open native gate — disjoint cues, 7/7 criteria (CASA-native-writer-criteria-v1)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from probe_infra import default_store, finalize_honest_probe_report, generated_report_path, setup_probe_imports
from probe_nositel_gate_ru import _scenario_pass

_PLAN = Path(__file__).resolve().parents[2] / "lessons/ru-text-tract/data/nositel-open-plan-v1.json"
_PROBE = "probe_nositel_open_ru"


def main() -> None:
    setup_probe_imports()
    from casa.domain.subject_articulation import compose_subject_utterance
    from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
    from casa.prisms.control.fpn_state import WorkingMemory
    from casa.prisms.shared.store_bundles import load_store_bundles
    from casa.prisms.shared.store_lock import store_session_lock
    from casa.prisms.tick.phrase_compose import paste_ratio_against_blocks
    from casa.prisms.tick.semantic_read import route_kb_read

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--plan", type=Path, default=_PLAN)
    args = p.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    scenarios = list(plan.get("scenarios") or [])
    min_ratio = float(plan.get("min_pass_ratio") or 1.0)
    store = default_store(args.store)
    items: list[dict[str, Any]] = []
    know = 0
    wired_total = 0
    wired_know = 0
    deferred = 0

    with store_session_lock(store, holder=f"probe:{_PROBE}"):
        from casa.cli.ingest_state import resolve_ingest_state
        from casa.prisms.memory.agent_memory_ops import agent_remember

        state = resolve_ingest_state(store, None)
        bundle = load_store_bundles(store)
        wm = WorkingMemory()

        for case in scenarios:
            if not case.get("wired", True):
                deferred += 1
                items.append(
                    {
                        "scenario_id": case.get("scenario_id"),
                        "dimension": case.get("dimension"),
                        "ru_n_criterion": case.get("ru_n_criterion"),
                        "verdict": "deferred",
                        "wired": False,
                        "defer_reason": case.get("defer_reason"),
                    }
                )
                continue

            remember_text = str(case.get("remember_text") or "")
            if remember_text:
                agent_remember(
                    store,
                    state,
                    {
                        "kind": "observation",
                        "text": remember_text,
                        "concepts": list(case.get("concepts") or []),
                        "tags": list(case.get("tags") or ["nositel-open"]),
                    },
                )

            q = str(case.get("recall_query") or case.get("query") or "")
            intent = route_kb_read(q, bundle, store_dir=store).intent
            ctx = gather_subject_dialogue_blocks(q, None, state, wm, store, bundle=bundle)
            reply = compose_subject_utterance(q, ctx)
            paste = paste_ratio_against_blocks(reply, ctx.blocks)

            max_paste = case.get("expect_max_paste_ratio")
            if max_paste is not None and paste > float(max_paste):
                ok = False
                detail = {
                    "scenario_id": case.get("scenario_id"),
                    "dimension": case.get("dimension"),
                    "ru_n_criterion": case.get("ru_n_criterion"),
                    "query_intent": intent,
                    "paste_ratio": round(paste, 3),
                    "failures": ["paste_max"],
                }
            else:
                ok, detail = _scenario_pass(case, reply=reply, query_intent=intent, paste_ratio=paste)
                detail["ru_n_criterion"] = case.get("ru_n_criterion")

            if tokens := case.get("expect_field_tokens"):
                rl = reply.lower()
                missing = [str(t) for t in tokens if str(t).lower() not in rl]
                if missing:
                    detail.setdefault("failures", []).append("field_tokens")
                    detail["missing_field_tokens"] = missing
                    ok = False

            wired_total += 1
            if ok:
                know += 1
                wired_know += 1

            items.append(
                {
                    "query": q[:140],
                    "verdict": "know" if ok else "wrong",
                    "reply_excerpt": reply[:360],
                    "wired": True,
                    **detail,
                }
            )

        by_dim: dict[str, dict[str, int]] = {}
        for row in items:
            if row.get("verdict") == "deferred":
                continue
            dim = str(row.get("dimension") or "other")
            bucket = by_dim.setdefault(dim, {"know": 0, "total": 0})
            bucket["total"] += 1
            if row.get("verdict") == "know":
                bucket["know"] += 1

        ratio = (wired_know / wired_total) if wired_total else 0.0
        ru_n_ready = wired_total > 0 and wired_know == wired_total and deferred == 0

        report: dict[str, Any] = {
            "store_id": store.name,
            "probe": _PROBE,
            "plan": str(args.plan),
            "gate_policy": plan.get("gate_policy"),
            "criteria_doc": plan.get("criteria_doc"),
            "dimensions": plan.get("dimensions"),
            "wired_total": wired_total,
            "wired_know": wired_know,
            "deferred": deferred,
            "know": wired_know,
            "total": wired_total,
            "wrong": wired_total - wired_know,
            "pass_ratio": round(ratio, 3),
            "min_pass_ratio": min_ratio,
            "by_dimension": by_dim,
            "items": items,
            "gate_pass": wired_total > 0 and ratio >= min_ratio and wired_know == wired_total,
            "ru_n_claim_pass": ru_n_ready,
        }
        report = finalize_honest_probe_report(state, report, store=store, probe_id=_PROBE)

    out = generated_report_path("teacher-probe-nositel-open-ru.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "probe": _PROBE,
                "wired_know": wired_know,
                "wired_total": wired_total,
                "deferred": deferred,
                "ru_n_claim_pass": report.get("ru_n_claim_pass"),
                "gate_pass": report.get("gate_pass"),
                "by_dimension": by_dim,
                "path": str(out),
            },
            ensure_ascii=False,
        )
    )
    raise SystemExit(0 if report.get("gate_pass") else 1)


if __name__ == "__main__":
    main()
