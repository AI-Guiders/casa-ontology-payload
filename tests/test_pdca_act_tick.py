#!/usr/bin/env python3
"""PDCA Act tick — centralized learning tail."""

from __future__ import annotations

from pathlib import Path

from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.tick import ControlExtensions
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.tick.pdca_act_tick import PdcaActConfig, PdcaActContext, maybe_pdca_act_tick


def _wm() -> WorkingMemory:
    return WorkingMemory(tick=1, goal_id="goal.read.word")


def _control(*, surprise: bool = False, value: float = 0.1) -> ControlExtensions:
    return ControlExtensions(
        predicted=("a",),
        surprise=("b",) if surprise else (),
        prediction_error=0.5 if surprise else 0.0,
        dan_mask=(),
        sparse_ratio=0.0,
        masked_digest=(),
        value=value,
    )


def test_pdca_act_tick_returns_canonical_keys(tmp_path: Path):
    state = ensure_prisms({})
    rep = maybe_pdca_act_tick(
        PdcaActContext(
            store_dir=tmp_path,
            state=state,
            wm=_wm(),
            wm_next=_wm(),
            control=_control(),
            mem_prep={"plan_tick": {"goal_id": "goal.read.word"}},
            cue="",
            bundle=None,
            hippo_ep=None,
            concept_ids=(),
            cfg=PdcaActConfig(agent_self_drive=False, kolb_relink_on_surprise=False),
        )
    )
    assert set(rep) == {"remember", "retain", "sleep", "adjust", "self_drive", "act_kind"}
    assert rep["act_kind"] is None


def test_pdca_act_kind_adjust_on_kolb_skip_false(tmp_path: Path, monkeypatch):
    state = ensure_prisms({})

    def _fake_kolb(ctx):
        return {"skipped": False, "handler": "tract.vis_lex"}

    monkeypatch.setattr(
        "casa.prisms.tick.pdca_act_tick.maybe_kolb_revise_tick",
        _fake_kolb,
    )
    rep = maybe_pdca_act_tick(
        PdcaActContext(
            store_dir=tmp_path,
            state=state,
            wm=_wm(),
            wm_next=_wm(),
            control=_control(surprise=True, value=0.5),
            mem_prep={},
            cue="test",
            bundle=None,
            hippo_ep={"id": "ep1"},
            concept_ids=("lang.word.x",),
            cfg=PdcaActConfig(
                remember_on_surprise=False,
                agent_self_drive=False,
                kolb_relink_on_surprise=True,
            ),
        )
    )
    assert rep["adjust"] is not None
    assert rep["act_kind"] == "adjust"
