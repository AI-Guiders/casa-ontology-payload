#!/usr/bin/env python3
"""Memory hygiene — routing audit, archive/compress hints (ADR-0037)."""

from __future__ import annotations

from typing import Any

from casa.domain.hypothesis_queue import open_hypothesis_count
from casa.domain.routing import (
    ROUTE_KIND_APPLICABILITY,
    ROUTE_KIND_CAPABILITY,
    ROUTE_KIND_GOAL,
    ROUTE_KIND_KNOWLEDGE,
    Router,
)


def _match_key(route) -> str:
    parts = [route.route_kind] + [f"{k}={v}" for k, v in sorted(route.match.items())]
    return "|".join(parts)


def audit_routes(state: dict) -> dict[str, Any]:
    router = Router.bind(state)
    by_kind: dict[str, int] = {}
    duplicates: list[dict[str, Any]] = []
    seen: dict[str, int] = {}

    for kind in (ROUTE_KIND_KNOWLEDGE, ROUTE_KIND_CAPABILITY, ROUTE_KIND_GOAL, ROUTE_KIND_APPLICABILITY):
        routes = router.routes(route_kind=kind)
        by_kind[kind] = len(routes)
        for route in routes:
            key = _match_key(route)
            if key in seen:
                duplicates.append(
                    {
                        "route_kind": kind,
                        "match": dict(route.match),
                        "first_index": seen[key],
                    }
                )
            else:
                seen[key] = len(seen)

    return {"by_kind": by_kind, "total": sum(by_kind.values()), "duplicate_matches": duplicates[:16]}


def memory_hygiene_panel(state: dict) -> dict[str, Any]:
    """Panel 3: routing, clutter, maintenance suggestions."""
    audit = audit_routes(state)
    cons = state.get("consolidation") if isinstance(state.get("consolidation"), dict) else {}
    hippo_merged = int(cons.get("episodes_merged_total") or 0)
    suggestions: list[str] = []

    dup_n = len(audit.get("duplicate_matches") or [])
    if dup_n:
        suggestions.append(f"review_duplicate_routes:{dup_n}")
    open_h = open_hypothesis_count(state)
    if open_h >= 4:
        suggestions.append("close_or_verify_open_hypotheses")
    if int(state.get("field_version") or 0) > 0 and hippo_merged == 0:
        suggestions.append("run_sleep_when_hippo_has_episodes")
    if state.get("_runtime_dirty"):
        suggestions.append("persist_runtime_checkpoint")
    if audit.get("total", 0) > 5000:
        suggestions.append("consider_compact_or_archive_ltm_meta")

    ok = dup_n == 0 and open_h < 8
    return {
        "panel": "memory",
        "ok": ok,
        "routes": audit,
        "open_hypotheses": open_h,
        "consolidation_merged_total": hippo_merged,
        "suggestions": suggestions,
        "search_hint": "router match keys; capability/applicability by goal_id",
    }
