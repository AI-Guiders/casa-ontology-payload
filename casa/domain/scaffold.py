#!/usr/bin/env python3
"""Scaffold fading levels — ZPD META (ADR-0034 C2)."""

from __future__ import annotations

from enum import Enum


class ScaffoldLevel(str, Enum):
    DEMONSTRATION = "demonstration"
    GUIDED = "guided"
    INDEPENDENT = "independent"


def infer_scaffold_level(
    *,
    capability_ready: bool = True,
    last_gate_passed: bool | None = None,
) -> ScaffoldLevel:
    if not capability_ready:
        return ScaffoldLevel.GUIDED
    if last_gate_passed is False:
        return ScaffoldLevel.GUIDED
    return ScaffoldLevel.INDEPENDENT
