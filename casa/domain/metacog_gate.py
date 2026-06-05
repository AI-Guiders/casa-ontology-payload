#!/usr/bin/env python3
"""Metacognition pre-check — tract readiness before Do (ADR-0034 C3)."""

from __future__ import annotations

from typing import Any

from casa.domain.scaffold import ScaffoldLevel, infer_scaffold_level
from casa.domain.scaffold_fading import current_scaffold_level, scaffold_plan_hint
from casa.domain.self_model import tract_confidence
from casa.prisms.memory.memory_prisms import memory_lattices
from casa.prisms.memory.stack import decode_lattice
from casa.prisms.visual.bridge_math import math_concept_votes


def capability_votes(state: dict, capability_id: str) -> int:
    """Rough field signal for skill.* route."""
    cap = str(capability_id or "").strip()
    if not cap.startswith("skill."):
        return 0
    lats = memory_lattices(state)
    total = 0
    for lat in lats.values():
        if not lat.get("cells"):
            continue
        dec = decode_lattice(lat, min_votes=1)
        for row in dec.get("concepts") or []:
            cid = str(row.get("concept_id") or "")
            if cap.replace("skill.", "") in cid or cid.startswith("skill."):
                total += int(row.get("votes") or 0)
    return total


def tract_ready(
    state: dict,
    step_capability: str,
    *,
    min_votes: int = 2,
) -> bool:
    cap = str(step_capability or "").strip()
    if not cap:
        return True
    sm_conf = tract_confidence(state, cap, default=-1.0)
    if sm_conf >= 0 and sm_conf < 0.45:
        return False
    if cap.startswith("skill.math."):
        return math_concept_votes(memory_lattices(state), "math.op.add", min_votes=1) > 0 or capability_votes(state, cap) >= min_votes
    return capability_votes(state, cap) >= min_votes


def metacog_pre_check(
    state: dict,
    *,
    step_capability: str,
    min_votes: int = 2,
    gate_passed: bool | None = None,
) -> dict[str, Any]:
    cap = str(step_capability or "").strip()
    ready = tract_ready(state, cap, min_votes=min_votes) if cap else True
    faded = current_scaffold_level(state)
    scaffold = infer_scaffold_level(
        capability_ready=ready,
        last_gate_passed=gate_passed,
    )
    if faded == ScaffoldLevel.INDEPENDENT:
        scaffold = faded
    hint = scaffold_plan_hint(state)
    return {
        "step_capability": cap,
        "tract_ready": ready,
        "scaffold_level": scaffold.value,
        "scaffold_hint": hint,
        "defer_predict": bool(cap and not ready and scaffold != ScaffoldLevel.DEMONSTRATION),
        "suggest": "seek_knowledge" if cap and not ready else None,
    }
