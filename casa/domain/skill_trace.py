#!/usr/bin/env python3
"""Skill application trace — situation → skill → outcome (ADR-0037 / ADR-0038)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from casa.domain.agent_journal import (
    append_skill_trace,
    last_skill_trace,
    query_skill_trace as journal_query_skill_trace,
    recent_skill_trace,
    skill_trace_aggregate,
)
from casa.prisms.control.fpn_state import WorkingMemory, read_session_meta, write_session_meta


def compact_routing(chain: dict[str, Any] | None) -> dict[str, Any]:
    """Shrink routing_chain to queryable keys."""
    if not isinstance(chain, dict):
        return {}
    goal = chain.get("goal") if isinstance(chain.get("goal"), dict) else {}
    app = chain.get("applicability") if isinstance(chain.get("applicability"), dict) else {}
    cap = chain.get("capability") if isinstance(chain.get("capability"), dict) else {}
    know = chain.get("knowledge") if isinstance(chain.get("knowledge"), dict) else {}
    matched_goal = goal.get("matched") if isinstance(goal.get("matched"), dict) else {}
    return {
        "goal_id": matched_goal.get("goal") or goal.get("target_goal"),
        "plan_id": app.get("target_plan"),
        "plan_steps": app.get("steps"),
        "capability_skill": cap.get("target_skill"),
        "knowledge_prism": know.get("prism_id") or know.get("content_prism"),
    }


def outcome_from_tick_report(report: dict[str, Any]) -> str:
    pdca = report.get("pdca") if isinstance(report.get("pdca"), dict) else {}
    check = pdca.get("check_tick") if isinstance(pdca.get("check_tick"), dict) else {}
    control = report.get("control") if isinstance(report.get("control"), dict) else {}
    self_drv = report.get("agent_self_drive") if isinstance(report.get("agent_self_drive"), dict) else {}
    promote = self_drv.get("skill_promote") if isinstance(self_drv.get("skill_promote"), dict) else {}
    if promote.get("promoted"):
        return "promoted"
    if check.get("check_passed"):
        return "verified"
    if control.get("surprise"):
        return "surprise"
    return "fail"


def build_skill_trace_entry(
    *,
    wm: WorkingMemory,
    report: dict[str, Any],
) -> dict[str, Any]:
    """One row: which skill in which situation, with verify outcome."""
    pdca = report.get("pdca") if isinstance(report.get("pdca"), dict) else {}
    check = pdca.get("check_tick") if isinstance(pdca.get("check_tick"), dict) else {}
    control = report.get("control") if isinstance(report.get("control"), dict) else {}
    metacog = check.get("metacog") if isinstance(check.get("metacog"), dict) else {}
    chain = report.get("routing_chain") if isinstance(report.get("routing_chain"), dict) else {}
    routing = compact_routing(chain)
    skill = wm.step_capability or routing.get("capability_skill") or ""

    return {
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tick": report.get("tick"),
        "situation": {
            "goal_id": wm.goal_id,
            "goal": wm.goal,
            "query": report.get("query"),
            "focus": wm.step_focus,
            "plan_id": wm.active_plan_id or routing.get("plan_id"),
        },
        "skill": skill,
        "plan_step": wm.step_index,
        "plan_steps": list(wm.plan_steps),
        "routing": routing,
        "outcome": outcome_from_tick_report(report),
        "verify": {
            "check_passed": bool(check.get("check_passed")),
            "surprise": bool(control.get("surprise")),
            "control_value": control.get("value"),
            "metacog_defer": bool(metacog.get("defer_predict")),
            "scaffold_level": check.get("scaffold_level") or report.get("scaffold_level"),
        },
        "weak_link": check.get("deliberate_practice") or report.get("deliberate_practice"),
        "act": pdca.get("act"),
        "skill_promote": (report.get("agent_self_drive") or {}).get("skill_promote")
        if isinstance(report.get("agent_self_drive"), dict)
        else None,
    }


def record_skill_trace_from_tick(
    store_dir: Path,
    *,
    wm: WorkingMemory,
    report: dict[str, Any],
    max_entries: int = 96,
) -> dict[str, Any]:
    """Persist skill application row into agent_journal.db."""
    entry = build_skill_trace_entry(wm=wm, report=report)
    if not entry.get("skill") and not entry.get("situation", {}).get("goal_id"):
        return entry
    append_skill_trace(store_dir, entry, max_rows=max_entries)
    meta = read_session_meta(store_dir)
    meta["last_skill_trace_at"] = entry.get("at")
    write_session_meta(store_dir, meta)
    return entry


def query_skill_trace(
    store_dir: Path,
    *,
    goal_id: str = "",
    skill: str = "",
    outcome: str = "",
    limit: int = 32,
) -> list[dict[str, Any]]:
    return journal_query_skill_trace(
        store_dir,
        goal_id=goal_id,
        skill=skill,
        outcome=outcome,
        limit=limit,
    )


def skill_trace_panel(store_dir: Path, *, limit: int = 12) -> dict[str, Any]:
    """Aggregates for diagnostics / cockpit."""
    agg = skill_trace_aggregate(store_dir)
    recent = recent_skill_trace(store_dir, limit=limit)
    last = last_skill_trace(store_dir)
    return {
        "panel": "skill_trace",
        "storage": "agent_journal.db",
        "ok": bool(agg.get("entries")),
        "entries": agg.get("entries", 0),
        "by_outcome": agg.get("by_outcome", {}),
        "by_goal": agg.get("by_goal", {}),
        "by_skill": agg.get("by_skill", {}),
        "last": last,
        "recent": recent,
        "search_hint": "skill_trace.goal_id, skill, outcome",
    }
