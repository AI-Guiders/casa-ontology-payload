#!/usr/bin/env python3
"""Subject diagnostics — cockpit panels (ADR-0037 / ADR-0038)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from casa.domain.carrier_health import assess_carrier_health
from casa.domain.experience_ledger import experience_panel
from casa.domain.memory_hygiene import memory_hygiene_panel
from casa.domain.skill_trace import skill_trace_panel
from casa.domain.subject_retrospective import retro_panel
from casa.prisms.control.fpn_state import WorkingMemory, load_session, read_session_meta, write_session_meta


def run_subject_diagnostics(
    state: dict,
    store_dir: Path,
    *,
    wm: WorkingMemory | None = None,
    include_nca: bool = False,
    experience_limit: int = 8,
) -> dict[str, Any]:
    """Run all panels; subject-facing cockpit snapshot."""
    wm = wm or load_session(store_dir)

    exp = experience_panel(store_dir, limit=experience_limit)
    body = assess_carrier_health(state, wm, store_dir=store_dir, include_nca=include_nca)
    mem = memory_hygiene_panel(state)
    skills = skill_trace_panel(store_dir, limit=experience_limit)
    retro = retro_panel(store_dir)

    warnings = list(body.get("warnings") or []) + list(mem.get("suggestions") or [])
    ok = bool(exp.get("ok")) and bool(body.get("ok")) and bool(mem.get("ok"))

    return {
        "schema_version": 2,
        "tool": "subject_diagnostics",
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "store": str(store_dir.resolve()),
        "journal": "agent_journal.db",
        "ok": ok,
        "warnings": warnings,
        "experience": exp,
        "body": body,
        "memory": mem,
        "skill_trace": skills,
        "retrospective": retro,
        "current_intent": {
            "goal_id": wm.goal_id,
            "goal": wm.goal,
            "step_capability": wm.step_capability,
            "step_focus": wm.step_focus,
            "plan_id": wm.active_plan_id,
        },
    }


def persist_diagnostics_snapshot(store_dir: Path, report: dict[str, Any]) -> Path:
    """Last diagnostics pointer in slim session."""
    from casa.prisms.control.fpn_state import session_path

    meta = read_session_meta(store_dir)
    meta["last_diagnostics_at"] = report.get("at")
    meta["last_diagnostics_ok"] = report.get("ok")
    write_session_meta(store_dir, meta)
    return session_path(store_dir)
