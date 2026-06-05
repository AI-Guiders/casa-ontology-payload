#!/usr/bin/env python3
"""PDCA (Deming) — domain-neutral continuous improvement META (ADR-0034).

Plan → Do → Check → Act wraps the subject learning steps 1–5 on every macro tick.
Domains plug in at Plan/Do content; the four phases are the same everywhere.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class PdcaPhase(str, Enum):
    PLAN = "plan"
    DO = "do"
    CHECK = "check"
    ACT = "act"


# Executor step mapping (domain-independent)
PDCA_TO_EXECUTOR_STEP: dict[PdcaPhase, str] = {
    PdcaPhase.PLAN: "1_2_3_goal_classify_methods",
    PdcaPhase.DO: "4_synthesize",
    PdcaPhase.CHECK: "5_verify",
    PdcaPhase.ACT: "act_standardize_or_adjust",
}


# What happens in Act (still domain-neutral)
PDCA_ACT_KIND = ("standardize", "adjust")


def infer_pdca_phase(
    *,
    plan_tick: dict[str, Any] | None,
    control: dict[str, Any] | None,
    kolb_revised: bool = False,
    skill_promoted: bool = False,
    sleep_ran: bool = False,
) -> PdcaPhase:
    """Best-effort phase label for tick report (telemetry, not control oracle)."""
    ctrl = control or {}
    surprise = bool(ctrl.get("surprise"))
    value = float(ctrl.get("value") or 0.0)

    if kolb_revised or skill_promoted or sleep_ran:
        return PdcaPhase.ACT

    if surprise and value >= 0.25:
        return PdcaPhase.CHECK

    pt = plan_tick if isinstance(plan_tick, dict) else {}
    if pt.get("step_capability") or pt.get("plan_steps"):
        return PdcaPhase.DO

    if pt.get("goal_id") or pt.get("active_plan_id"):
        return PdcaPhase.PLAN

    return PdcaPhase.DO


def pdca_act_kind(
    *,
    kolb_revised: bool = False,
    skill_promoted: bool = False,
    sleep_ran: bool = False,
    check_passed: bool = False,
) -> str | None:
    """Act sub-kind: standardize (pass) vs adjust (fail → revise)."""
    if kolb_revised:
        return "adjust"
    if skill_promoted or (sleep_ran and check_passed):
        return "standardize"
    return None
