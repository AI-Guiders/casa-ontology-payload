#!/usr/bin/env python3
"""Sublimation — defer partner turn toward deliberate practice (ADR-0074)."""

from __future__ import annotations

from typing import Any

from casa.domain.self_model import tract_confidence
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.defense.core import defense_block, limbic_sublimation_active


def defense_sublimation_prefers_defer(
    state: dict,
    wm: WorkingMemory,
    *,
    load_rep: dict[str, Any],
) -> bool:
    """When limbic band active, prefer defer unless tract is already strong."""
    if not limbic_sublimation_active(state):
        return False
    capability = str(wm.step_capability or "").strip()
    if capability and tract_confidence(state, capability) >= 0.55:
        return False
    if load_rep.get("overloaded"):
        return True
    block = defense_block(state)
    block["sublimation_last"] = {"active": True, "mechanism": "sublimation"}
    try:
        from casa.prisms.defense.sandbox import defense_sandbox_on_sublimation_defer

        block["sublimation_sandbox"] = defense_sandbox_on_sublimation_defer(
            state, wm, tick=int(state.get("field_version") or 0)
        )
    except ImportError:
        pass
    return True
