#!/usr/bin/env python3
"""Hippocampus quad-mode dispatch (ADR-0088): wake | consolidate | integrate | idle_micro."""

from __future__ import annotations

from typing import Any, Literal

HippoMode = Literal["wake", "consolidate", "integrate", "idle_micro"]

HIPPO_MODE_WAKE: HippoMode = "wake"
HIPPO_MODE_CONSOLIDATE: HippoMode = "consolidate"
HIPPO_MODE_INTEGRATE: HippoMode = "integrate"
HIPPO_MODE_IDLE_MICRO: HippoMode = "idle_micro"

VALID_HIPPO_MODES: frozenset[str] = frozenset(
    {HIPPO_MODE_WAKE, HIPPO_MODE_CONSOLIDATE, HIPPO_MODE_INTEGRATE, HIPPO_MODE_IDLE_MICRO}
)


def get_hippo_mode(state: dict[str, Any]) -> str:
    """Current hippo mode from ``state['sn']['hippo_mode']`` (default wake)."""
    sn = state.get("sn") if isinstance(state.get("sn"), dict) else {}
    mode = str(sn.get("hippo_mode") or HIPPO_MODE_WAKE).strip().lower()
    return mode if mode in VALID_HIPPO_MODES else HIPPO_MODE_WAKE


def set_hippo_mode(state: dict[str, Any], mode: str) -> str:
    """Set ``sn.hippo_mode``; returns canonical mode string."""
    canonical = str(mode or HIPPO_MODE_WAKE).strip().lower()
    if canonical not in VALID_HIPPO_MODES:
        raise ValueError(f"unknown hippo_mode: {mode!r}")
    state["sn"] = {**(state.get("sn") or {}), "hippo_mode": canonical, "mode": canonical}
    return canonical
