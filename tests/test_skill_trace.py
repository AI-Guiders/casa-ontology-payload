#!/usr/bin/env python3
"""Skill trace — situation → skill → outcome."""

from __future__ import annotations

from pathlib import Path

from casa.domain.skill_trace import (
    build_skill_trace_entry,
    query_skill_trace,
    record_skill_trace_from_tick,
    skill_trace_panel,
)
from casa.prisms.control.fpn_state import WorkingMemory


def test_build_skill_trace_entry_links_goal_skill_outcome():
    wm = WorkingMemory(
        goal_id="goal.read.phrase",
        goal="мыла раму",
        step_capability="skill.read.analytic",
        step_index=0,
        active_plan_id="plan.phrase_compose_von-neumann",
        step_focus="phrase-probe-x",
    )
    report = {
        "tick": 4,
        "query": "phrase:мыла раму",
        "routing_chain": {
            "applicability": {
                "target_plan": "plan.phrase_compose_von-neumann",
                "steps": ["skill.read.analytic", "skill.compose.slots"],
            },
            "knowledge": {"prism_id": "prism_lang_ru"},
        },
        "control": {"surprise": ["x"], "value": 0.9},
        "pdca": {"check_tick": {"check_passed": False, "scaffold_level": "guided"}},
    }
    entry = build_skill_trace_entry(wm=wm, report=report)
    assert entry["skill"] == "skill.read.analytic"
    assert entry["situation"]["goal_id"] == "goal.read.phrase"
    assert entry["outcome"] == "surprise"
    assert entry["routing"]["knowledge_prism"] == "prism_lang_ru"


def test_record_and_query_skill_trace(tmp_path: Path):
    store = tmp_path / "agent"
    store.mkdir()
    wm = WorkingMemory(goal_id="goal.read.phrase", step_capability="skill.read.analytic")
    report = {
        "tick": 1,
        "query": "q",
        "pdca": {"check_tick": {"check_passed": True}},
        "control": {},
    }
    record_skill_trace_from_tick(store, wm=wm, report=report)
    rows = query_skill_trace(store, skill="analytic", outcome="verified")
    assert len(rows) == 1
    panel = skill_trace_panel(store)
    assert panel["by_skill"]["skill.read.analytic"]["verified"] == 1


def test_query_filters_goal_and_outcome(tmp_path: Path):
    store = tmp_path / "agent"
    store.mkdir()
    from casa.domain.agent_journal import append_skill_trace

    append_skill_trace(
        store,
        {
            "skill": "skill.read.analytic",
            "outcome": "fail",
            "situation": {"goal_id": "goal.read.phrase"},
        },
    )
    append_skill_trace(
        store,
        {
            "skill": "skill.verify.phrase",
            "outcome": "verified",
            "situation": {"goal_id": "goal.read.phrase"},
        },
    )
    rows = query_skill_trace(store, goal_id="goal.read.phrase", outcome="verified")
    assert len(rows) == 1
    assert rows[0]["skill"] == "skill.verify.phrase"
