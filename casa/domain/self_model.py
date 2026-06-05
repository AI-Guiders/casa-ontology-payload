#!/usr/bin/env python3
"""Self-model — tract confidence from gates only (ADR-0036)."""

from __future__ import annotations

from typing import Any

from casa.domain.knowledge_tracing import record_trace_attempt, trace_row


def _model(state: dict) -> dict[str, dict[str, Any]]:
    raw = state.setdefault("self_model", {})
    if isinstance(raw, dict) and "tracts" in raw:
        tracts = raw.get("tracts")
        return tracts if isinstance(tracts, dict) else {}
    return raw if isinstance(raw, dict) else {}


def update_tract_from_gate(
    state: dict,
    tract_id: str,
    *,
    passed: bool,
    tick: int,
    provenance: str,
) -> dict[str, Any]:
    tid = str(tract_id or "").strip()
    if not tid:
        return {}
    key = tid if tid.startswith("skill.") else f"skill.{tid}"
    record_trace_attempt(state, f"tract:{key}", passed=passed, tick=tick)
    row = trace_row(state, f"tract:{key}")
    confidence = float(row.get("p_known") or 0.5)

    tracts = _model(state)
    entry = {
        "confidence": round(confidence, 4),
        "last_gate": "pass" if passed else "fail",
        "updated_tick": tick,
        "provenance": provenance,
        "streak": row.get("streak"),
    }
    tracts[key] = entry
    state["self_model"] = {"tracts": tracts, "updated_tick": tick}
    state.setdefault("sn", {})["self_model"] = entry
    return entry


def tract_confidence(state: dict, tract_id: str, *, default: float = 0.5) -> float:
    tid = str(tract_id or "").strip()
    if not tid:
        return default
    key = tid if tid.startswith("skill.") else f"skill.{tid}"
    entry = _model(state).get(key) or {}
    return float(entry.get("confidence") or default)


def self_model_summary(state: dict) -> dict[str, Any]:
    tracts = _model(state)
    weak = sorted(tracts.items(), key=lambda x: float(x[1].get("confidence") or 0))[:4]
    return {
        "tract_count": len(tracts),
        "weakest": [{"tract": k, **v} for k, v in weak],
    }
