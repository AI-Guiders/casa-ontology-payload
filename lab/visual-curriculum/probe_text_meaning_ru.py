#!/usr/bin/env python3
"""Block B11 text meaning gate — props + articulate (ADR-0053)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from probe_infra import default_store, finalize_honest_probe_report, generated_report_path, setup_probe_imports
from text_meaning_scenario import scenario_pass

_PLAN = Path(__file__).resolve().parents[2] / "lessons/ru-text-comprehend/data/text-meaning-plan-v1.json"
_PROBE = "probe_text_meaning_ru"
_HELD_OUT = Path(__file__).resolve().parents[2] / "lessons/ru-text-comprehend/data/text-meaning-held-out-plan.json"
_STAGE = "stage-11-text-meaning-ru"


def main() -> None:
    setup_probe_imports()
    from casa.domain.subject_articulation import compose_subject_utterance
    from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
    from casa.prisms.control.fpn_state import WorkingMemory
    from casa.prisms.shared.store_bundles import load_store_bundles
    from casa.prisms.shared.store_lock import store_session_lock
    from casa.prisms.tick.passage import extract_passage_meaning
    from casa.prisms.tick.phrase_compose import paste_ratio_against_blocks
    from casa.prisms.tick.semantic_read import route_kb_read

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--plan", type=Path, default=_PLAN)
    p.add_argument("--held-out", action="store_true", help="Use disjoint held-out scenarios")
    args = p.parse_args()

    plan_path = _HELD_OUT if args.held_out and _HELD_OUT.is_file() else args.plan
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    scenarios = list(plan.get("scenarios") or [])
    min_ratio = float(plan.get("min_pass_ratio") or 1.0)

    store = default_store(args.store)
    items: list[dict[str, Any]] = []
    know = 0
    total = 0
    by_stage: dict[str, dict[str, int]] = {}

    with store_session_lock(store, holder=f"probe:{_PROBE}"):
        from casa.cli.ingest_state import resolve_ingest_state

        state = resolve_ingest_state(store, None)
        bundle = load_store_bundles(store)
        wm = WorkingMemory()

        for case in scenarios:
            if not case.get("wired", True):
                items.append(
                    {
                        "scenario_id": case.get("scenario_id"),
                        "stage": case.get("stage"),
                        "verdict": "deferred",
                        "wired": False,
                    }
                )
                continue

            q = str(case.get("query") or "")
            intent = route_kb_read(q, bundle, store_dir=store).intent
            props = extract_passage_meaning(q, intent=intent, bundle=bundle, store_dir=store)
            prop_ids = [r.concept_id for r in props]
            ctx = gather_subject_dialogue_blocks(q, None, state, wm, store, bundle=bundle)
            reply = compose_subject_utterance(q, ctx)
            paste = paste_ratio_against_blocks(reply, ctx.blocks)
            ok, detail = scenario_pass(
                case,
                reply=reply,
                query_intent=intent,
                paste_ratio=paste,
                prop_ids=prop_ids,
            )
            total += 1
            stage = str(case.get("stage") or "other")
            bucket = by_stage.setdefault(stage, {"know": 0, "total": 0})
            bucket["total"] += 1
            if ok:
                know += 1
                bucket["know"] += 1
            items.append(
                {
                    "query": q[:140],
                    "verdict": "know" if ok else "wrong",
                    "reply_excerpt": reply[:360],
                    "scenario_id": case.get("scenario_id"),
                    "stage": stage,
                    "sub_act": case.get("sub_act"),
                    "descriptor_ru": case.get("descriptor_ru"),
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
            "class_id": "ru-text-comprehend",
            "plan": str(plan_path),
            "target_skill": plan.get("target_skill"),
            "gate_policy": plan.get("gate_policy"),
            "know": know,
            "total": total,
            "wrong": total - know,
            "pass_ratio": round(ratio, 3),
            "min_pass_ratio": min_ratio,
            "by_stage": by_stage,
            "items": items,
            "gate_pass": gate_pass,
            "promote_hints": [
                {
                    "kind": "capability",
                    "match": {
                        "modality": "text",
                        "geometry": "passage_context",
                        "locale": "ru",
                    },
                    "target_skill": "skill.read.comprehend",
                },
                {
                    "kind": "applicability",
                    "match": {"goal": "goal.read.comprehend", "locale": "ru"},
                    "target_plan": f"plan.text_comprehend_{store.name}",
                    "steps": ["skill.read.comprehend", "skill.read.phrase"],
                },
                {
                    "kind": "goal",
                    "match": {"inbox_kind": "text", "stage": _STAGE},
                    "target_goal": "goal.read.comprehend",
                },
            ],
        }
        report = finalize_honest_probe_report(state, report, store=store, probe_id=_PROBE)

    out = generated_report_path("teacher-probe-text-meaning-ru.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "probe": _PROBE,
                "gate_pass": report.get("gate_pass"),
                "know": know,
                "total": total,
                "by_stage": by_stage,
                "path": str(out),
            },
            ensure_ascii=False,
        )
    )
    raise SystemExit(0 if report.get("gate_pass") else 1)


if __name__ == "__main__":
    main()
