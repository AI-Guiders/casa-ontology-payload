#!/usr/bin/env python3
"""Subject retrospective (Scrum 3Q) tests."""

from __future__ import annotations

from pathlib import Path

from casa.domain.agent_journal import append_skill_trace
from casa.domain.goal_arbiter import arbitrate_plan_intent, collect_retro_intent_candidates
from casa.domain.subject_retrospective import (
    maybe_run_retrospective,
    maybe_run_retrospective_after_sleep,
    maybe_run_retrospective_on_wake,
    persist_retrospective,
    run_retrospective,
)
from casa.prisms.control.fpn_state import WorkingMemory


def _trace_row(goal_id: str, skill: str, outcome: str, *, step: int = 0, weak: dict | None = None) -> dict:
    return {
        "situation": {"goal_id": goal_id},
        "skill": skill,
        "plan_step": step,
        "outcome": outcome,
        "weak_link": weak,
    }


def test_retrospective_stop_and_try(tmp_path: Path):
    store = tmp_path / "agent"
    store.mkdir()
    for _ in range(2):
        append_skill_trace(
            store,
            _trace_row(
                "goal.read.phrase",
                "skill.read.analytic",
                "surprise",
                weak={"concept_id": "syllable.ла"},
            ),
        )
    retro = run_retrospective(store, window=8, min_keep=2, min_stop=2)
    assert len(retro["stop"]) == 1
    assert any(t.get("action") == "practice" for t in retro["try"])


def test_retrospective_persist_and_arbiter(tmp_path: Path):
    store = tmp_path / "agent"
    store.mkdir()
    for _ in range(3):
        append_skill_trace(
            store,
            _trace_row(
                "goal.read.phrase",
                "skill.read.analytic",
                "fail",
                weak={"concept_id": "syllable.ла", "frame_id": "f1"},
            ),
        )
    retro = run_retrospective(store)
    persist_retrospective(store, retro)

    cands = collect_retro_intent_candidates(store)
    assert any(c.source == "retro" for c in cands)

    state: dict = {}
    wm = WorkingMemory()
    rep = arbitrate_plan_intent(state, wm, store)
    assert rep.get("candidates", 0) >= 0


def test_maybe_run_skips_without_entries(tmp_path: Path):
    store = tmp_path / "agent"
    store.mkdir()
    assert maybe_run_retrospective(store) is None
    assert maybe_run_retrospective_on_wake(store) is None


def test_on_wake_skips_when_fresh(tmp_path: Path):
    store = tmp_path / "agent"
    store.mkdir()
    for _ in range(3):
        append_skill_trace(store, _trace_row("goal.read.phrase", "skill.read.analytic", "fail"))
    assert maybe_run_retrospective_on_wake(store) is not None
    assert maybe_run_retrospective_on_wake(store) is None
    append_skill_trace(store, _trace_row("goal.read.phrase", "skill.read.analytic", "fail"))
    assert maybe_run_retrospective_on_wake(store) is not None


def test_after_sleep_skips_when_fresh(tmp_path: Path):
    store = tmp_path / "agent"
    store.mkdir()
    for _ in range(3):
        append_skill_trace(store, _trace_row("goal.read.phrase", "skill.read.analytic", "fail"))
    assert maybe_run_retrospective_after_sleep(store) is not None
    assert maybe_run_retrospective_after_sleep(store) is None
