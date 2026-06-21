#!/usr/bin/env python3
"""Staging: apply a candidate lesson in ISOLATION, gate it, promote only on pass.

A candidate (an LLM-drafted or curated lesson) is applied to a deep copy of the
live field, verified by the teaching tool's gate, and merged into the live field
ONLY if it passes. A failing candidate is discarded and never touches the live
store — so the auto-curriculum can try candidates without risking corruption.

This is the in-memory staging the orchestration loop (Phase 3) drives; the on-disk
counterpart is validate_bundle + the import-delta ingest gate (already wired) plus
versioned bundle writes.
"""

from __future__ import annotations

import copy
from typing import Any


def stage_and_promote(
    live_state: dict,
    lesson: dict[str, Any],
    *,
    bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stage ``lesson`` against a copy of ``live_state``; promote to live iff it passes.

    Returns ``{promoted, learned, report}``. On promote, ``live_state`` is mutated
    in place to the staged result; on reject, ``live_state`` is left untouched.
    """
    from casa.curriculum.teach import teach

    staged = copy.deepcopy(live_state)
    report = teach(staged, bundle=bundle, **lesson)
    learned = bool(report.get("learned"))
    if learned:
        live_state.clear()
        live_state.update(staged)
    return {"promoted": learned, "learned": learned, "report": report}
