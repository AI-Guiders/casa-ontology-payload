#!/usr/bin/env python3
"""B11 text-meaning gate — prop extraction + articulate criteria (ADR-0053)."""

from __future__ import annotations

from typing import Any

from probe_nositel_gate_ru import _scenario_pass as _nositel_pass


def scenario_pass(
    case: dict[str, Any],
    *,
    reply: str,
    query_intent: str,
    paste_ratio: float,
    prop_ids: list[str],
) -> tuple[bool, dict[str, Any]]:
    """Gate one B11 scenario: KB props + dialogue shape (reuses nositel checks)."""
    ok, detail = _nositel_pass(
        case,
        reply=reply,
        query_intent=query_intent,
        paste_ratio=paste_ratio,
    )
    detail["prop_ids"] = list(prop_ids)
    failures = list(detail.get("failures") or [])

    if expect := case.get("expect_props"):
        required = [str(p) for p in expect]
        missing = [p for p in required if p not in prop_ids]
        detail["missing_props"] = missing
        if missing:
            failures.append("props")
            ok = False

    if expect_any := case.get("expect_props_any"):
        options = [str(p) for p in expect_any]
        if not any(p in prop_ids for p in options):
            failures.append("props_any")
            detail["missing_props_any"] = options
            ok = False

    max_paste = case.get("expect_max_paste_ratio")
    if max_paste is not None and paste_ratio > float(max_paste):
        failures.append("paste_max")
        ok = False

    detail["failures"] = failures
    return ok, detail
