#!/usr/bin/env python3
"""Maturity metrics — is the curriculum actually working?

Capability coverage over a probe set is the developmental signal: the fraction of
probes the field surfaces (injection ablated). It rises as the auto-curriculum
closes gaps, and is computed on the SAME held-out machinery the gate uses, so a
rise means real recall/generalization — not a self-report.
"""

from __future__ import annotations

from typing import Any


def coverage(
    state: dict,
    probes: list[dict[str, Any]],
    *,
    bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fraction of ``probes`` the field surfaces. Returns counts + the open gaps."""
    from casa.curriculum.loop import mine_targets

    gaps = mine_targets(state, probes, bundle=bundle)
    total = len(probes)
    failed = len(gaps)
    passed = total - failed
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "coverage": round(passed / total, 4) if total else 0.0,
        "gaps": [g.get("concept_id") for g in gaps],
    }
