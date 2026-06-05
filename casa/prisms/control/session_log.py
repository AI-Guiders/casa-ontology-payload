#!/usr/bin/env python3
"""Append macro tick learning log (ADR-0034 B5 / ADR-0038 journal)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from casa.domain.agent_journal import append_tick_log_entry, bump_macro_ticks
from casa.domain.skill_trace import compact_routing, outcome_from_tick_report
from casa.prisms.control.fpn_state import WorkingMemory, save_session


def append_tick_log(
    store_dir: Path,
    *,
    wm: WorkingMemory,
    report: dict[str, Any],
    max_entries: int = 64,
) -> dict[str, Any]:
    pdca = report.get("pdca") if isinstance(report.get("pdca"), dict) else {}
    phase = str(pdca.get("phase") or "")
    srl = "performance"
    if phase == "plan":
        srl = "forethought"
    elif phase == "check":
        srl = "self_reflection"
    elif pdca.get("act"):
        srl = "adaptation"

    org = report.get("self_organization") if isinstance(report.get("self_organization"), dict) else {}
    plan_arb = org.get("plan_arbiter") if isinstance(org.get("plan_arbiter"), dict) else {}
    winner = plan_arb.get("winner") if isinstance(plan_arb.get("winner"), dict) else {}

    entry = {
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tick": report.get("tick"),
        "query": report.get("query"),
        "executor": {
            "goal_id": wm.goal_id,
            "step_capability": wm.step_capability,
            "plan_steps": wm.plan_steps,
            "step_index": wm.step_index,
        },
        "srl": srl,
        "pdca": {
            "phase": pdca.get("phase"),
            "act": pdca.get("act"),
        },
        "methodology": {
            "spacing_goal": report.get("spacing_goal"),
            "progression_goal": report.get("progression_goal"),
            "deliberate_practice": report.get("deliberate_practice"),
            "scaffold_level": report.get("scaffold_level"),
        },
        "arbiter": {
            "winner_source": winner.get("source"),
            "subject_disposition": (plan_arb.get("subject_disposition") or {}).get("action"),
        },
        "check": {
            "surprise": bool((report.get("control") or {}).get("surprise")),
            "hippo": report.get("hippo_episode") is not None,
            "check_passed": bool(
                ((report.get("pdca") or {}).get("check_tick") or {}).get("check_passed")
            ),
        },
        "routing_chain": compact_routing(
            report.get("routing_chain") if isinstance(report.get("routing_chain"), dict) else None
        ),
        "outcome": outcome_from_tick_report(report),
    }

    append_tick_log_entry(store_dir, entry, max_rows=max_entries)
    bump_macro_ticks(store_dir, at=entry["at"])
    save_session(store_dir, wm)
    return entry
