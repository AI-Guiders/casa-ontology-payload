#!/usr/bin/env python3
"""PDCA META — phase inference."""

from __future__ import annotations

from casa.domain.pdca_cycle import PdcaPhase, infer_pdca_phase, pdca_act_kind


def test_infer_plan_when_goal_only():
    phase = infer_pdca_phase(plan_tick={"goal_id": "goal.read.word"}, control={})
    assert phase == PdcaPhase.PLAN


def test_infer_do_when_step_active():
    phase = infer_pdca_phase(
        plan_tick={"goal_id": "g", "step_capability": "skill.read.analytic"},
        control={},
    )
    assert phase == PdcaPhase.DO


def test_infer_check_on_surprise():
    phase = infer_pdca_phase(
        plan_tick={},
        control={"surprise": ["lang.word.x"], "value": 0.5},
    )
    assert phase == PdcaPhase.CHECK


def test_infer_act_on_kolb():
    phase = infer_pdca_phase(plan_tick={}, control={}, kolb_revised=True)
    assert phase == PdcaPhase.ACT
    assert pdca_act_kind(kolb_revised=True) == "adjust"
    assert pdca_act_kind(skill_promoted=True) == "standardize"
