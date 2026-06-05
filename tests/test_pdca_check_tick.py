#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.tick import ControlExtensions
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.tick.pdca_check_tick import PdcaCheckConfig, PdcaCheckContext, maybe_pdca_check_tick


def test_pdca_check_keys(tmp_path: Path):
    state = ensure_prisms({})
    control = ControlExtensions(
        predicted=(),
        surprise=(),
        prediction_error=0.0,
        dan_mask=(),
        sparse_ratio=0.0,
        masked_digest=(),
        value=0.1,
    )
    rep = maybe_pdca_check_tick(
        PdcaCheckContext(
            store_dir=tmp_path,
            state=state,
            wm=WorkingMemory(),
            control=control,
            cue="",
            lattice_id="lexicon-ru",
            bundle=None,
            mem_prep={},
            cfg=PdcaCheckConfig(goal_from_surprise=False, surprise_episode=False),
        )
    )
    assert rep["check_passed"] is True
    assert "metacog" in rep
