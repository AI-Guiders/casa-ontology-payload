#!/usr/bin/env python3
"""Experience ledger — subject-facing narrative episodes (ADR-0037 / ADR-0038)."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from casa.domain.agent_journal import (
    append_experience_entry,
    count_tick_log,
    experience_outcome_counts,
    recent_experience,
)
from casa.domain.skill_trace import compact_routing
from casa.prisms.control.fpn_state import WorkingMemory, read_session_meta


def _slug(text: str, *, max_len: int = 32) -> str:
    base = re.sub(r"[^\w.\-]+", "-", str(text or "").strip().lower())
    base = re.sub(r"-+", "-", base).strip("-")
    if len(base) <= max_len:
        return base or "episode"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
    return f"{base[: max_len - 9]}-{digest}"


def _outcome_from_report(report: dict[str, Any]) -> str:
    pdca = report.get("pdca") if isinstance(report.get("pdca"), dict) else {}
    control = report.get("control") if isinstance(report.get("control"), dict) else {}
    self_drv = report.get("agent_self_drive") if isinstance(report.get("agent_self_drive"), dict) else {}
    promote = (self_drv.get("skill_promote") or {}) if isinstance(self_drv.get("skill_promote"), dict) else {}
    if promote.get("promoted"):
        return "promoted"
    if control.get("surprise"):
        return "surprise"
    check = pdca.get("check_tick") if isinstance(pdca.get("check_tick"), dict) else {}
    if check.get("check_passed"):
        return "verified"
    if pdca.get("act") in ("sleep", "remember", "adjust"):
        return str(pdca.get("act"))
    return "continued"


def _reasoning_chain(report: dict[str, Any], wm: WorkingMemory) -> dict[str, Any]:
    org = report.get("self_organization") if isinstance(report.get("self_organization"), dict) else {}
    plan_arb = org.get("plan_arbiter") if isinstance(org.get("plan_arbiter"), dict) else {}
    winner = plan_arb.get("winner") if isinstance(plan_arb.get("winner"), dict) else {}
    seed = org.get("autonomy_seed") if isinstance(org.get("autonomy_seed"), dict) else {}
    pdca = report.get("pdca") if isinstance(report.get("pdca"), dict) else {}
    chain: dict[str, Any] = {
        "intent": winner.get("source") or seed.get("source"),
        "goal_id": wm.goal_id,
        "method": wm.step_capability or wm.step_focus,
        "routing": compact_routing(report.get("routing_chain") if isinstance(report.get("routing_chain"), dict) else None),
    }
    check = pdca.get("check_tick") if isinstance(pdca.get("check_tick"), dict) else {}
    if check:
        chain["verify"] = "pass" if check.get("check_passed") else "fail"
    if pdca.get("act"):
        chain["act"] = pdca.get("act")
    disp = (org.get("plan_arbiter") or {}).get("subject_disposition")
    if isinstance(disp, dict) and disp.get("action"):
        chain["subject"] = disp.get("action")
    return chain


def build_experience_entry(
    *,
    wm: WorkingMemory,
    report: dict[str, Any],
) -> dict[str, Any]:
    goal = wm.goal_id or str(report.get("query") or "")
    name = _slug(goal or wm.goal or "tick")
    tags = [t for t in {goal, wm.goal, wm.step_capability, wm.step_focus, name} if t]
    return {
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tick": report.get("tick"),
        "name": name,
        "title": wm.goal or goal or name,
        "search_tags": tags[:12],
        "outcome": _outcome_from_report(report),
        "reasoning_chain": _reasoning_chain(report, wm),
        "step": {
            "capability": wm.step_capability,
            "focus": wm.step_focus,
            "index": wm.step_index,
            "plan_id": wm.active_plan_id,
        },
    }


def record_experience_from_tick(
    store_dir: Path,
    *,
    wm: WorkingMemory,
    report: dict[str, Any],
) -> dict[str, Any]:
    """Persist experience episode into agent_journal.db."""
    entry = build_experience_entry(wm=wm, report=report)
    append_experience_entry(store_dir, entry)
    return entry


def experience_panel(store_dir: Path, *, limit: int = 8) -> dict[str, Any]:
    """Panel 1: what I did, outcomes, names for search."""
    meta = read_session_meta(store_dir)
    recent = recent_experience(store_dir, limit=limit)
    last = recent[-1] if recent else {}
    tick_count = count_tick_log(store_dir)
    outcomes = experience_outcome_counts(store_dir)
    ledger_n = sum(outcomes.values())
    return {
        "panel": "experience",
        "storage": "agent_journal.db",
        "ok": bool(recent or tick_count),
        "macro_ticks": int(meta.get("macro_ticks") or 0),
        "tick_log_entries": tick_count,
        "ledger_entries": ledger_n,
        "outcome_counts": outcomes,
        "last": last,
        "recent": list(reversed(recent)),
        "search_hint": "experience.name, title, outcome",
    }
