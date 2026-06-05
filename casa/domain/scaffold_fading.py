#!/usr/bin/env python3
"""Scaffold fading — demonstration → guided → independent (ZPD)."""

from __future__ import annotations

from typing import Any

from casa.domain.scaffold import ScaffoldLevel


def _scaffold_store(state: dict) -> dict[str, Any]:
    raw = state.setdefault("scaffold", {})
    return raw if isinstance(raw, dict) else {}


def current_scaffold_level(state: dict) -> ScaffoldLevel:
    level = str(_scaffold_store(state).get("level") or ScaffoldLevel.GUIDED.value)
    try:
        return ScaffoldLevel(level)
    except ValueError:
        return ScaffoldLevel.GUIDED


def update_scaffold_after_check(
    state: dict,
    *,
    passed: bool,
) -> str:
    store = _scaffold_store(state)
    level = current_scaffold_level(state)
    passes = int(store.get("consecutive_passes") or 0)

    if passed:
        passes += 1
        if passes >= 3 and level == ScaffoldLevel.GUIDED:
            level = ScaffoldLevel.INDEPENDENT
        elif passes >= 1 and level == ScaffoldLevel.DEMONSTRATION:
            level = ScaffoldLevel.GUIDED
    else:
        passes = 0
        level = ScaffoldLevel.GUIDED

    store.update({"level": level.value, "consecutive_passes": passes, "last_passed": passed})
    state["scaffold"] = store
    state.setdefault("sn", {})["scaffold_level"] = level.value
    return level.value


def scaffold_plan_hint(state: dict) -> dict[str, Any]:
    level = current_scaffold_level(state)
    return {"scaffold_level": level.value}
