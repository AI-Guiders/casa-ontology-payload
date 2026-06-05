#!/usr/bin/env python3
from __future__ import annotations

from casa.domain.spacing_policy import due_concepts, maybe_spacing_goal, record_spacing_seen, rehearsal_goal_id
from casa.prisms.control.fpn_state import WorkingMemory


def test_spacing_due_and_goal():
    state: dict = {}
    record_spacing_seen(state, "lang.word.abc", tick=1, passed=False)
    assert not due_concepts(state, tick=2)
    assert due_concepts(state, tick=5)
    wm = WorkingMemory(tick=5)
    rep = maybe_spacing_goal(state, wm)
    assert rep is not None
    assert wm.goal_id == rehearsal_goal_id("lang.word.abc")
