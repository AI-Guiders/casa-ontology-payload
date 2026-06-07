#!/usr/bin/env python3
"""RU intent personal gate — agent tract priors after dialogue (ADR-0057)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from probe_infra import finalize_honest_probe_report, generated_report_path, setup_probe_imports

_PLAN = Path(__file__).resolve().parents[2] / "lessons/ru-text-tract/data/intent-personal-plan-v1.json"
_PROBE = "probe_intent_personal_ru"
_STAGE = "stage-05f-intent-personal-ru"


def _fresh_state():
    from casa.prisms.memory.intent import spawn_intent_lattice
    from casa.prisms.memory.memory_prisms import ensure_prisms

    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 1})
    spawn_intent_lattice(state, tick=0)
    return state


def _apply_policy(state, override: dict[str, Any] | None) -> None:
    if not override:
        return
    from casa.prisms.memory.agent_prism import ensure_agent_prism

    block = ensure_agent_prism(state)
    policy = dict(block.get("intent_policy") or {})
    policy.update(override)
    block["intent_policy"] = policy


def _run_case(case: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    from casa.prisms.memory.intent import (
        intent_after_partner_turn,
        intent_tract_boosts,
        is_agent_tract,
        list_agent_tracts,
    )
    from casa.prisms.tick.tract import compete_tract_intent

    train = dict(case.get("train") or {})
    q_train = str(train.get("query") or "")
    turns = int(train.get("turns") or 2)
    bind_top = int(train.get("bind_top") or 24)
    winner = str(train.get("winner") or "")

    state = _fresh_state()
    _apply_policy(state, train.get("intent_policy_override"))

    last_ranked: list[Any] = []
    last_intent = "general"
    for tick in range(1, turns + 1):
        last_intent, last_ranked = compete_tract_intent(q_train, None, state=state)
        tract = winner or last_intent
        intent_after_partner_turn(state, q_train, tract, tick=tick, ranked=last_ranked, bind_top=bind_top)

    eval_q = str(case.get("eval_query") or q_train)
    intent, ranked = compete_tract_intent(eval_q, None, state=state)
    boosts = intent_tract_boosts(state, eval_q)

    ok = True
    detail: dict[str, Any] = {
        "eval_intent": intent,
        "intent_boosts": {k: v for k, v in boosts.items() if v},
        "agent_tracts": len(list_agent_tracts(state)),
    }

    if case.get("expect_agent_tract"):
        ok = is_agent_tract(intent)
        detail["expect"] = "agent_tract_winner"

    min_boost = case.get("min_intent_boost")
    if min_boost is not None:
        host = last_intent if not winner else winner
        got = boosts.get(host, 0)
        detail["host_tract"] = host
        detail["host_boost"] = got
        ok = ok and got >= int(min_boost)
        detail["expect"] = detail.get("expect") or "host_boost"

    detail["intent_prism_sources"] = any("intent_prism" in s for t in ranked for s in t.sources)
    return ok, detail


def main() -> None:
    setup_probe_imports()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan", type=Path, default=_PLAN)
    args = p.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    scenarios = list(plan.get("scenarios") or [])
    min_ratio = float(plan.get("min_pass_ratio") or 1.0)

    items: list[dict[str, Any]] = []
    know = 0
    total = 0
    state_for_report = _fresh_state()

    for case in scenarios:
        if not case.get("wired", True):
            continue
        total += 1
        ok, detail = _run_case(case)
        if ok:
            know += 1
        items.append(
            {
                "scenario_id": case.get("scenario_id"),
                "stage": case.get("stage") or _STAGE,
                "verdict": "know" if ok else "wrong",
                "wired": True,
                **detail,
            }
        )

    ratio = (know / total) if total else 0.0
    gate_pass = total > 0 and ratio >= min_ratio and know == total
    report: dict[str, Any] = {
        "probe": _PROBE,
        "stage": _STAGE,
        "class_id": "ru-text-tract",
        "plan": str(args.plan),
        "know": know,
        "total": total,
        "pass_ratio": round(ratio, 3),
        "min_pass_ratio": min_ratio,
        "items": items,
        "gate_pass": gate_pass,
    }
    report = finalize_honest_probe_report(state_for_report, report, store=None, probe_id=_PROBE)

    out = generated_report_path("teacher-probe-intent-personal-ru.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for case, item in zip(scenarios, items, strict=False):
        if not case.get("wired", True):
            continue
        print("\n=== Intent personal:", case.get("scenario_id"), "|", item.get("verdict"), "===\n")
        print(json.dumps(item, ensure_ascii=False, indent=2))

    print(
        json.dumps(
            {"probe": _PROBE, "gate_pass": gate_pass, "know": know, "total": total, "path": str(out)},
            ensure_ascii=False,
        )
    )
    raise SystemExit(0 if gate_pass else 1)


if __name__ == "__main__":
    main()
