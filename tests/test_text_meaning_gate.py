#!/usr/bin/env python3
"""B11 text-meaning gate — prop criteria + emergent promote wiring."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_VC = _REPO / "lab/visual-curriculum"
if str(_VC) not in sys.path:
    sys.path.insert(0, str(_VC))

from text_meaning_scenario import scenario_pass  # noqa: E402

from casa.domain.emergent_promote import (  # noqa: E402
    _probe_route_actions,
    suggest_trial_plan,
)
from casa.domain.mastery_gate import probe_gate_for_skill
from casa.domain.teacher_gate import probe_gate_passed


def _plan() -> dict:
    path = _REPO / "lessons/ru-text-comprehend/data/text-meaning-plan-v1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_probe_gate_for_comprehend_skill() -> None:
    assert probe_gate_for_skill("skill.read.comprehend") == "probe_text_meaning_ru"
    assert probe_gate_for_skill("skill.spell.check") == "probe_orthography_ru"
    assert probe_gate_for_skill("skill.punct.check") == "probe_grammar_punct_ru"


def test_suggest_trial_plan_comprehend() -> None:
    plan = suggest_trial_plan("goal.read.comprehend", ("skill.read.comprehend", "skill.read.phrase"))
    assert plan is not None
    assert "skill.read.comprehend" in plan.steps


def test_emergent_routes_on_gate_pass() -> None:
    report = {"probe": "probe_text_meaning_ru", "gate_pass": True}
    actions = _probe_route_actions(report, "probe_text_meaning_ru", "von-neumann")
    skills = [a.get("target_skill") for a in actions if a.get("kind") == "capability"]
    assert "skill.read.comprehend" in skills


def test_emergent_ortho_route() -> None:
    report = {"probe": "probe_orthography_ru", "gate_pass": True}
    actions = _probe_route_actions(report, "probe_orthography_ru", "agent")
    assert any(a.get("target_skill") == "skill.spell.check" for a in actions)


def test_teacher_gate_pass_from_report() -> None:
    assert probe_gate_passed({"probe": "probe_text_meaning_ru", "gate_pass": True, "know": 6, "total": 6})
    assert not probe_gate_passed({"probe": "probe_text_meaning_ru", "gate_pass": False, "know": 4, "total": 6})


@pytest.mark.parametrize(
    "scenario_id,prop_ids",
    [
        ("b11-extract-purchase", ["ru.prop.fact.purchase"]),
        ("b11-inference-praise", ["ru.prop.inference.praise_for_showing"]),
    ],
)
def test_scenario_pass_requires_props(scenario_id: str, prop_ids: list[str]) -> None:
    case = next(c for c in _plan()["scenarios"] if c["scenario_id"] == scenario_id)
    ok, detail = scenario_pass(
        case,
        reply="апельсин — ответ своими словами",
        query_intent="discuss",
        paste_ratio=0.1,
        prop_ids=prop_ids,
    )
    assert ok, detail

    ok2, detail2 = scenario_pass(
        case,
        reply="апельсин",
        query_intent="discuss",
        paste_ratio=0.1,
        prop_ids=[],
    )
    assert not ok2
    assert "props" in detail2.get("failures", [])
