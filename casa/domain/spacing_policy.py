#!/usr/bin/env python3
"""Spacing + retrieval schedule — uses knowledge tracing (ADR-0034 C1)."""

from __future__ import annotations

import hashlib
from typing import Any

from casa.domain.knowledge_tracing import due_for_retrieval, record_trace_attempt, trace_row
from casa.prisms.control.fpn_state import WorkingMemory


def record_spacing_seen(
    state: dict,
    concept_id: str,
    *,
    tick: int,
    passed: bool,
) -> dict[str, Any]:
    """Update KT ledger after Check (spacing + mastery signal)."""
    return record_trace_attempt(state, concept_id, passed=passed, tick=tick)


def due_concepts(state: dict, *, tick: int) -> list[tuple[str, dict[str, Any]]]:
    """Concepts due for retrieval — lower p_known first."""
    out: list[tuple[str, dict[str, Any]]] = []
    ledger = state.get("knowledge_trace") if isinstance(state.get("knowledge_trace"), dict) else {}
    for cid, row in ledger.items():
        if str(cid).startswith("gate:"):
            continue
        if not isinstance(row, dict):
            continue
        if due_for_retrieval(state, cid, tick=tick):
            out.append((cid, row))
    out.sort(key=lambda x: float(x[1].get("p_known") or 1.0))
    return out


def rehearsal_goal_id(concept_id: str) -> str:
    digest = hashlib.sha256(concept_id.encode("utf-8")).hexdigest()[:10]
    return f"goal.rehearse.{digest}"


def maybe_spacing_goal(
    state: dict,
    wm: WorkingMemory,
    *,
    force: bool = False,
) -> dict[str, Any] | None:
    """Plan hook: rehearsal goal when retrieval due and WM has no goal."""
    if wm.goal_id and not force:
        return None
    due = due_concepts(state, tick=wm.tick)
    if not due:
        return None
    cid, row = due[0]
    gid = rehearsal_goal_id(cid)
    wm.goal_id = gid
    wm.goal = f"rehearse:{cid}"
    return {
        "goal_id": gid,
        "concept_id": cid,
        "p_known": row.get("p_known"),
        "interval": trace_row(state, cid).get("interval"),
        "kind": "retrieval_schedule",
    }
