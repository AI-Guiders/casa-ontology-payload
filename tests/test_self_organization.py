#!/usr/bin/env python3
"""ADR-0036 self-organization organs."""

from __future__ import annotations

from pathlib import Path

from casa.domain.goal_arbiter import arbitrate_plan_intent, collect_plan_candidates
from casa.domain.hypothesis_queue import enqueue_hypothesis, open_hypothesis_count, verify_hypothesis
from casa.domain.intent_checkpoint import checkpoint_restore_candidate, save_intent_checkpoint
from casa.domain.load_governor import assess_cognitive_load, allows_candidate
from casa.domain.self_model import tract_confidence, update_tract_from_gate
from casa.prisms.control.fpn_state import WorkingMemory


def test_explicit_goal_is_proposal_not_command():
    state: dict = {}
    wm = WorkingMemory(goal_id="goal.inbox.test", goal="inbox")
    candidates = collect_plan_candidates(state, wm, Path("/tmp/none"))
    explicit = next(c for c in candidates if c.source == "explicit")
    assert explicit.priority == 75


def test_subject_defers_inbox_when_practice_pending(tmp_path: Path):
    state = {
        "last_weakest_link": {"concept_id": "syllable.ла", "frame_id": "syllable-ла-sans"},
    }
    wm = WorkingMemory(goal_id="goal.inbox.test", goal="inbox", tick=1)
    rep = arbitrate_plan_intent(state, wm, tmp_path)
    assert rep["subject_disposition"]["action"] == "defer"
    assert rep["winner"]["source"] == "deliberate_practice"


def test_subject_refuses_external_when_requested(tmp_path: Path):
    state = {"subject": {"refuse_external": True}}
    wm = WorkingMemory(goal_id="goal.inbox.test", goal="inbox", tick=1)
    rep = arbitrate_plan_intent(state, wm, tmp_path)
    assert rep["subject_disposition"]["action"] == "refuse"
    assert rep["winner"] is None or rep["winner"]["source"] != "explicit"


def test_load_governor_blocks_low_priority():
    load = {"overloaded": True, "load": 5}
    assert not allows_candidate(40, load)
    assert allows_candidate(80, load)


def test_hypothesis_queue_open_close():
    state: dict = {}
    enqueue_hypothesis(state, expect="read мама", concept_id="lang.word.x", tick=1)
    assert open_hypothesis_count(state) == 1
    verify_hypothesis(state, concept_id="lang.word.x", passed=True, tick=2)
    assert open_hypothesis_count(state) == 0


def test_self_model_confidence():
    state: dict = {}
    update_tract_from_gate(state, "skill.read.analytic", passed=False, tick=1, provenance="test")
    assert tract_confidence(state, "skill.read.analytic") < 0.6
    update_tract_from_gate(state, "skill.read.analytic", passed=True, tick=2, provenance="test")
    assert tract_confidence(state, "skill.read.analytic") > 0.4


def test_intent_checkpoint_restore(tmp_path: Path):
    wm = WorkingMemory(goal_id="goal.read.phrase", step_capability="skill.read.analytic", tick=10)
    save_intent_checkpoint(tmp_path, wm, why="after_ingest", tick=10)
    empty = WorkingMemory(tick=12)
    cand = checkpoint_restore_candidate(tmp_path, empty)
    assert cand is not None
    assert cand["goal_id"] == "goal.read.phrase"


def test_arbitrate_plan_with_weakest_link(tmp_path: Path):
    state = {"last_weakest_link": {"concept_id": "syllable.ла", "frame_id": "syllable-ла-sans"}}
    wm = WorkingMemory(tick=1)
    rep = arbitrate_plan_intent(state, wm, tmp_path)
    assert rep["winner"]["source"] == "deliberate_practice"
    assert wm.step_focus == "syllable-ла-sans"


def test_cognitive_load_counts_hypotheses():
    state: dict = {}
    enqueue_hypothesis(state, expect="a", concept_id="c1", tick=1)
    enqueue_hypothesis(state, expect="b", concept_id="c2", tick=1)
    wm = WorkingMemory(plan_steps=["s1", "s2", "s3"])
    load = assess_cognitive_load(state, wm)
    assert load["load"] >= 2
