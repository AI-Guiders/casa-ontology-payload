#!/usr/bin/env python3
"""Self-check before CEN — stealth verify / metacog (ADR-0036 §7)."""

from __future__ import annotations

from typing import Any

from casa.domain.metacog_gate import metacog_pre_check
from casa.domain.plan_tick import PlanTick
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.tick.agent_self_drive_tick import _plan_from_mem_prep, _verify_plan_step


def maybe_self_check_before_cen(
    state: dict,
    *,
    wm: WorkingMemory,
    mem_prep: dict[str, Any],
    cue: str = "",
    bundle: dict | None = None,
) -> dict[str, Any]:
    """Metacog + optional step verify before SN/CEN act."""
    cap = str(wm.step_capability or "").strip()
    metacog = metacog_pre_check(state, step_capability=cap)
    out: dict[str, Any] = {
        "step_capability": cap,
        "metacog": metacog,
        "defer_cen": bool(metacog.get("defer_predict")),
    }

    if not cap:
        out["skipped"] = True
        out["reason"] = "no_step_capability"
        return out

    plan = _plan_from_mem_prep(mem_prep)
    if plan.step_capability and plan.step_focus:
        passed = _verify_plan_step(
            state,
            plan=plan,
            cue=cue,
            bundle=bundle,
            knowledge={},
            mem_prep=mem_prep,
        )
        out["step_verify"] = passed
        if not passed and metacog.get("defer_predict"):
            out["defer_cen"] = True
            out["action"] = "seek_or_practice"
    elif metacog.get("defer_predict"):
        out["action"] = metacog.get("suggest") or "seek_knowledge"

    state.setdefault("sn", {})["self_check"] = {
        "defer_cen": out.get("defer_cen"),
        "tract_ready": metacog.get("tract_ready"),
        "scaffold_level": metacog.get("scaffold_level"),
    }
    return out
