#!/usr/bin/env python3
"""Lightweight knowledge tracing — p_known + spacing interval (ADR-0034)."""

from __future__ import annotations

from typing import Any

_MIN_INTERVAL = 3
_MAX_INTERVAL = 48


def _ledger(state: dict) -> dict[str, dict[str, Any]]:
    raw = state.setdefault("knowledge_trace", {})
    return raw if isinstance(raw, dict) else {}


def p_known(row: dict[str, Any]) -> float:
    successes = int(row.get("successes") or 0)
    failures = int(row.get("failures") or 0)
    return (successes + 1) / (successes + failures + 2)


def interval_from_p_known(prob: float) -> int:
    if prob < 0.35:
        return _MIN_INTERVAL
    if prob < 0.55:
        return 6
    if prob < 0.75:
        return 12
    if prob < 0.9:
        return 24
    return _MAX_INTERVAL


def record_trace_attempt(
    state: dict,
    key: str,
    *,
    passed: bool,
    tick: int,
) -> dict[str, Any]:
    """Update KT ledger for concept or gate key."""
    k = str(key or "").strip()
    if not k:
        return {}
    ledger = _ledger(state)
    row = dict(ledger.get(k) or {})
    successes = int(row.get("successes") or 0)
    failures = int(row.get("failures") or 0)
    streak = int(row.get("streak") or 0)
    if passed:
        successes += 1
        streak = streak + 1 if streak >= 0 else 1
    else:
        failures += 1
        streak = -1
    prob = (successes + 1) / (successes + failures + 2)
    row.update(
        {
            "successes": successes,
            "failures": failures,
            "streak": streak,
            "p_known": round(prob, 4),
            "interval": interval_from_p_known(prob),
            "last_tick": tick,
            "last_passed": passed,
        }
    )
    ledger[k] = row
    state["knowledge_trace"] = ledger
    return row


def trace_row(state: dict, key: str) -> dict[str, Any]:
    return dict(_ledger(state).get(str(key or "").strip()) or {})


def due_for_retrieval(state: dict, key: str, *, tick: int) -> bool:
    row = trace_row(state, key)
    if not row:
        return False
    last = int(row.get("last_tick") or 0)
    interval = int(row.get("interval") or _MIN_INTERVAL)
    return tick - last >= interval
