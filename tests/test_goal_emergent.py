#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from casa.domain.goal_emergent import maybe_goal_from_surprise
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.tick import ControlExtensions
from casa.prisms.memory.memory_prisms import ensure_prisms


def test_goal_from_surprise_mints_revise(tmp_path: Path):
    state = ensure_prisms({})
    wm = WorkingMemory()
    control = ControlExtensions(
        predicted=("math.op.add",),
        surprise=("math.op.sub",),
        prediction_error=0.6,
        dan_mask=(),
        sparse_ratio=0.0,
        masked_digest=(),
        value=0.5,
    )
    rep = maybe_goal_from_surprise(tmp_path, state, wm=wm, control=control, hippo_ep=None, cue="2+2")
    assert rep is not None
    assert wm.goal_id.startswith("goal.revise.")
    assert rep["concept_id"] == "math.op.sub"
