#!/usr/bin/env python3
"""Gate = KSA verification (ADR-0037): mastery streak before promote (CBE).

Agent gate: held-out + verdict from store/predict.
Sidecar probe without store — no credit in gate:skill.* (see casa/domain/teacher_gate.py).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.domain.knowledge_tracing import record_trace_attempt, trace_row

DEFAULT_MASTERY_STREAK = 2

# Lab probe id → capability promoted on tick (unified gate credit).
PROBE_GATE_BY_SKILL: dict[str, str] = {
    "skill.read.whole": "probe_lexical_read_fluent_ru",
    "skill.read.analytic": "analytic-read-corpus-r1",
    "skill.read.phrase": "phrase-agent-store",
    "skill.compose.slots": "phrase-agent-store",
    "skill.verify.phrase": "phrase-agent-store",
    "skill.agree.subjectVerb": "phrase-agent-store",
    "skill.agree.modifierHead": "phrase-agent-store",
    "skill.select.form": "paradigm-select",
}

SKILL_GATE_BY_PROBE: dict[str, str] = {v: k for k, v in PROBE_GATE_BY_SKILL.items()}


def skill_gate_id(skill: str) -> str:
    return f"skill:{str(skill or '').strip()}"


def probe_gate_for_skill(skill: str) -> str | None:
    return PROBE_GATE_BY_SKILL.get(str(skill or "").strip())


def promote_gate_id(*, skill: str, probe_gate: str | None = None) -> str:
    """Canonical gate for tick promote — skill namespace; probe syncs into it."""
    _ = probe_gate
    return skill_gate_id(skill)


def record_gate_attempt(
    state: dict,
    gate_id: str,
    *,
    passed: bool,
    tick: int = 0,
    store_dir: Path | None = None,
) -> dict[str, Any]:
    gid = str(gate_id or "probe").strip()
    row = record_trace_attempt(state, f"gate:{gid}", passed=passed, tick=tick)
    if store_dir is not None:
        from casa.domain.gate_journal import append_gate_attempt

        append_gate_attempt(store_dir, gate_id=gid, passed=passed, tick=tick, row=row)
    return row


def sync_probe_pass_to_skill_gate(
    state: dict,
    probe_gate_id: str,
    *,
    tick: int = 0,
    store_dir: Path | None = None,
) -> None:
    """Lab probe green → credit matching skill gate (one namespace for tick promote)."""
    skill = SKILL_GATE_BY_PROBE.get(str(probe_gate_id or "").strip())
    if not skill:
        return
    record_gate_attempt(state, skill_gate_id(skill), passed=True, tick=tick, store_dir=store_dir)


def mastery_ready(
    state: dict,
    gate_id: str,
    *,
    min_streak: int = DEFAULT_MASTERY_STREAK,
) -> bool:
    row = trace_row(state, f"gate:{str(gate_id or '').strip()}")
    if not row:
        return False
    streak = int(row.get("streak") or 0)
    return streak >= min_streak and bool(row.get("last_passed"))


def mastery_ready_for_skill(
    state: dict,
    skill: str,
    *,
    min_streak: int = DEFAULT_MASTERY_STREAK,
) -> bool:
    gid = skill_gate_id(skill)
    if mastery_ready(state, gid, min_streak=min_streak):
        return True
    probe = probe_gate_for_skill(skill)
    return bool(probe and mastery_ready(state, probe, min_streak=min_streak))


def mastery_status(
    state: dict,
    gate_id: str,
    *,
    min_streak: int = DEFAULT_MASTERY_STREAK,
) -> dict[str, Any]:
    row = trace_row(state, f"gate:{str(gate_id or '').strip()}")
    streak = int(row.get("streak") or 0)
    return {
        "gate_id": gate_id,
        "streak": streak,
        "min_streak": min_streak,
        "ready": mastery_ready(state, gate_id, min_streak=min_streak),
        "p_known": row.get("p_known"),
    }
