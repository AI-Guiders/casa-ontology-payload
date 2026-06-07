#!/usr/bin/env python3
"""RU-α material→verbal gate — journal recall + field articulate (Galperin bridge)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from probe_infra import default_store, finalize_honest_probe_report, generated_report_path, setup_probe_imports
from text_meaning_scenario import scenario_pass

_PLAN = Path(__file__).resolve().parents[2] / "lessons/ru-material-verbal/data/material-verbal-moment-plan-v1.json"
_HELD_OUT = Path(__file__).resolve().parents[2] / "lessons/ru-material-verbal/data/material-verbal-held-out-plan.json"
_PROBE = "probe_material_verbal_ru"
_STAGE = "stage-05a-material-verbal-ru"


def _run_case(
    case: dict[str, Any],
    *,
    store,
    state,
    wm,
    bundle,
) -> tuple[bool, dict[str, Any], str]:
    from casa.domain.subject_articulation import compose_subject_utterance
    from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
    from casa.prisms.memory.agent_memory_ops import agent_remember
    from casa.prisms.tick.phrase_compose import paste_ratio_against_blocks
    from casa.prisms.tick.semantic_read import route_kb_read

    remember_text = str(case.get("remember_text") or "")
    if remember_text:
        agent_remember(
            store,
            state,
            {
                "kind": "observation",
                "text": remember_text,
                "concepts": list(case.get("concepts") or []),
                "tags": list(case.get("tags") or ["material-verbal"]),
            },
        )

    q = str(case.get("recall_query") or "")
    intent = route_kb_read(q, bundle, store_dir=store).intent
    ctx = gather_subject_dialogue_blocks(q, None, state, wm, store, bundle=bundle)
    reply = compose_subject_utterance(q, ctx)
    paste = paste_ratio_against_blocks(reply, ctx.blocks)

    ok, detail = scenario_pass(
        case,
        reply=reply,
        query_intent=intent,
        paste_ratio=paste,
        prop_ids=[],
    )

    tokens = case.get("expect_field_tokens") or []
    rl = reply.lower()
    missing = [str(t) for t in tokens if str(t).lower() not in rl]
    if missing:
        detail.setdefault("failures", []).append("field_tokens")
        detail["missing_field_tokens"] = missing
        ok = False

    return ok, detail, reply


def main() -> None:
    setup_probe_imports()
    from casa.prisms.control.fpn_state import WorkingMemory
    from casa.prisms.shared.store_bundles import load_store_bundles
    from casa.prisms.shared.store_lock import store_session_lock

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--plan", type=Path, default=_PLAN)
    p.add_argument("--held-out", action="store_true")
    args = p.parse_args()

    plan_path = _HELD_OUT if args.held_out and _HELD_OUT.is_file() else args.plan
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    scenarios = list(plan.get("scenarios") or [])
    min_ratio = float(plan.get("min_pass_ratio") or 1.0)

    store = default_store(args.store)
    items: list[dict[str, Any]] = []
    know = 0
    total = 0

    with store_session_lock(store, holder=f"probe:{_PROBE}"):
        from casa.cli.ingest_state import resolve_ingest_state

        state = resolve_ingest_state(store, None)
        bundle = load_store_bundles(store)
        wm = WorkingMemory()

        for case in scenarios:
            if not case.get("wired", True):
                continue
            total += 1
            ok, detail, reply = _run_case(case, store=store, state=state, wm=wm, bundle=bundle)
            if ok:
                know += 1
            items.append(
                {
                    "scenario_id": case.get("scenario_id"),
                    "stage": case.get("stage"),
                    "verdict": "know" if ok else "wrong",
                    "reply_excerpt": reply[:360],
                    "wired": True,
                    **detail,
                }
            )

        ratio = (know / total) if total else 0.0
        gate_pass = total > 0 and ratio >= min_ratio and know == total
        report: dict[str, Any] = {
            "store_id": store.name,
            "probe": _PROBE,
            "stage": _STAGE,
            "class_id": "ru-material-verbal",
            "plan": str(plan_path),
            "know": know,
            "total": total,
            "pass_ratio": round(ratio, 3),
            "items": items,
            "gate_pass": gate_pass,
            "promote_hints": [
                {
                    "kind": "capability",
                    "match": {"modality": "text", "locale": "ru", "read_intent": "explain"},
                    "target_skill": "skill.articulate.field",
                },
                {
                    "kind": "goal",
                    "match": {"inbox_kind": "journal", "stage": _STAGE},
                    "target_goal": "goal.articulate.experience",
                },
            ],
        }
        report = finalize_honest_probe_report(state, report, store=store, probe_id=_PROBE)

    out = generated_report_path("teacher-probe-material-verbal-ru.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"probe": _PROBE, "gate_pass": report.get("gate_pass"), "know": know, "total": total, "path": str(out)},
            ensure_ascii=False,
        )
    )
    raise SystemExit(0 if report.get("gate_pass") else 1)


if __name__ == "__main__":
    main()
