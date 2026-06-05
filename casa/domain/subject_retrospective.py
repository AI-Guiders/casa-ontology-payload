#!/usr/bin/env python3
"""Subject retrospective — Scrum 3Q over skill_trace (ADR-0037 / ADR-0038)."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from casa.domain.agent_journal import (
    append_retrospective_entry,
    count_retrospectives,
    last_retrospective,
    recent_skill_trace,
)
from casa.domain.spacing_policy import rehearsal_goal_id

_DEFAULT_WINDOW = 16
_MIN_ENTRIES = 3


def _bucket_key(row: dict[str, Any]) -> tuple[str, str, int]:
    sit = row.get("situation") if isinstance(row.get("situation"), dict) else {}
    gid = str(sit.get("goal_id") or "")
    skill = str(row.get("skill") or "")
    step = int(row.get("plan_step") or 0)
    return gid, skill, step


def run_retrospective(
    store_dir: Path,
    *,
    window: int = _DEFAULT_WINDOW,
    min_keep: int = 2,
    min_stop: int = 2,
) -> dict[str, Any]:
    """Synthesize Keep / Stop / Try from recent skill applications."""
    recent = recent_skill_trace(store_dir, limit=max(1, window))
    by_key: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in recent:
        by_key[_bucket_key(row)].append(row)

    keep: list[dict[str, Any]] = []
    stop: list[dict[str, Any]] = []

    for (gid, skill, step), rows in sorted(by_key.items()):
        outcomes = [str(r.get("outcome") or "") for r in rows]
        good = sum(1 for o in outcomes if o in ("verified", "promoted"))
        bad = sum(1 for o in outcomes if o in ("fail", "surprise"))
        if not gid and not skill:
            continue
        if good >= min_keep and good > bad:
            keep.append(
                {
                    "goal_id": gid,
                    "skill": skill,
                    "plan_step": step,
                    "evidence": f"{good}× verified/promoted in last {len(rows)} tries",
                    "count": len(rows),
                    "good": good,
                    "bad": bad,
                }
            )
        if bad >= min_stop and bad >= good:
            weak = None
            for r in reversed(rows):
                if str(r.get("outcome") or "") in ("fail", "surprise"):
                    wl = r.get("weak_link")
                    if isinstance(wl, dict) and wl:
                        weak = wl
                        break
            stop.append(
                {
                    "goal_id": gid,
                    "skill": skill,
                    "plan_step": step,
                    "pattern": f"{skill}@{step}+fail",
                    "evidence": f"{bad}× fail/surprise in last {len(rows)} tries",
                    "count": len(rows),
                    "good": good,
                    "bad": bad,
                    "weak_link": weak,
                }
            )

    try_items: list[dict[str, Any]] = []
    for item in stop[:4]:
        wl = item.get("weak_link") if isinstance(item.get("weak_link"), dict) else {}
        cid = str(wl.get("concept_id") or "")
        if cid:
            try_items.append(
                {
                    "action": "practice",
                    "reason": "retro_stop",
                    "goal_id": f"goal.practice.{cid.split('.')[-1][:20]}",
                    "goal": f"practice:{cid}",
                    "step_capability": str(item.get("skill") or "skill.read.analytic"),
                    "step_focus": str(wl.get("frame_id") or ""),
                    "concept_id": cid,
                    "from_stop": item,
                }
            )
        elif item.get("skill"):
            try_items.append(
                {
                    "action": "change_approach",
                    "reason": "retro_stop",
                    "goal_id": str(item.get("goal_id") or ""),
                    "goal": f"retry:{item.get('goal_id')}",
                    "step_capability": str(item.get("skill") or ""),
                    "note": "recurring fail without weak_link — seek knowledge / scaffold",
                    "from_stop": item,
                }
            )

    for item in keep[:3]:
        gid = str(item.get("goal_id") or "")
        if gid:
            try_items.append(
                {
                    "action": "continue",
                    "reason": "retro_keep",
                    "goal_id": gid,
                    "goal": f"continue:{gid}",
                    "step_capability": str(item.get("skill") or ""),
                    "from_keep": item,
                }
            )

    seen_cids: set[str] = {str(t.get("concept_id") or "") for t in try_items if t.get("concept_id")}
    ledger = recent_skill_trace(store_dir, limit=window * 2)
    concept_failures: dict[str, int] = defaultdict(int)
    for row in ledger:
        wl = row.get("weak_link")
        if isinstance(wl, dict) and wl.get("concept_id"):
            if str(row.get("outcome") or "") in ("fail", "surprise"):
                concept_failures[str(wl["concept_id"])] += 1
    for cid, n in sorted(concept_failures.items(), key=lambda x: -x[1]):
        if n >= min_stop and cid not in seen_cids:
            try_items.append(
                {
                    "action": "rehearse",
                    "reason": "retro_recurring_weak",
                    "goal_id": rehearsal_goal_id(cid),
                    "goal": f"rehearse:{cid}",
                    "concept_id": cid,
                    "evidence": f"{n}× fail on concept",
                }
            )
            seen_cids.add(cid)
            if len([t for t in try_items if t.get("action") == "rehearse"]) >= 2:
                break

    return {
        "schema_version": 1,
        "tool": "subject_retrospective",
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window": window,
        "entries_analyzed": len(recent),
        "questions": {
            "keep": "What went well? (preserve / reinforce)",
            "stop": "What went poorly? (recurring fail patterns)",
            "try": "What will we do differently?",
        },
        "keep": keep,
        "stop": stop,
        "try": try_items,
    }


def persist_retrospective(store_dir: Path, retro: dict[str, Any]) -> None:
    append_retrospective_entry(store_dir, retro)
    from casa.domain.agent_journal import count_skill_trace
    from casa.prisms.control.fpn_state import read_session_meta, write_session_meta

    meta = read_session_meta(store_dir)
    meta["last_retrospective_at"] = retro.get("at")
    meta["skill_trace_at_last_retro"] = count_skill_trace(store_dir)
    if retro.get("trigger"):
        meta["last_retrospective_trigger"] = retro.get("trigger")
    write_session_meta(store_dir, meta)


def _retro_is_due(
    store_dir: Path,
    *,
    min_entries: int = _MIN_ENTRIES,
    min_new: int = 1,
) -> bool:
    from casa.domain.agent_journal import count_retrospectives, count_skill_trace

    total = count_skill_trace(store_dir)
    if total < min_entries:
        return False
    if count_retrospectives(store_dir) == 0:
        return True
    from casa.prisms.control.fpn_state import read_session_meta

    meta = read_session_meta(store_dir)
    at_last = int(meta.get("skill_trace_at_last_retro") or 0)
    return (total - at_last) >= min_new


def maybe_run_retrospective_when_due(
    store_dir: Path,
    *,
    trigger: str,
    window: int = _DEFAULT_WINDOW,
    min_entries: int = _MIN_ENTRIES,
    min_new: int = 1,
    force: bool = False,
) -> dict[str, Any] | None:
    """Run S3Q when journal has enough new skill_trace since last retro."""
    if not force and not _retro_is_due(store_dir, min_entries=min_entries, min_new=min_new):
        return None
    retro = run_retrospective(store_dir, window=window)
    retro["trigger"] = trigger
    persist_retrospective(store_dir, retro)
    return retro


def maybe_run_retrospective_on_wake(
    store_dir: Path,
    *,
    window: int = _DEFAULT_WINDOW,
    force: bool = False,
) -> dict[str, Any] | None:
    """Wake insurance: retro if never run or new traces since last."""
    from casa.domain.agent_journal import count_retrospectives

    min_new = 0 if count_retrospectives(store_dir) == 0 else 1
    return maybe_run_retrospective_when_due(
        store_dir,
        trigger="wake",
        window=window,
        min_new=min_new,
        force=force,
    )


def maybe_run_retrospective_after_sleep(
    store_dir: Path,
    *,
    window: int = _DEFAULT_WINDOW,
) -> dict[str, Any] | None:
    """Post-consolidation epoch: reflect on recent skill applications."""
    return maybe_run_retrospective_when_due(
        store_dir,
        trigger="after_sleep",
        window=window,
        min_new=1,
    )


def maybe_run_retrospective(
    store_dir: Path,
    *,
    window: int = _DEFAULT_WINDOW,
    min_entries: int = _MIN_ENTRIES,
    force: bool = False,
) -> dict[str, Any] | None:
    """CLI entry — recompute when enough skill_trace (or --force)."""
    if not force:
        recent = recent_skill_trace(store_dir, limit=window)
        if len(recent) < min_entries:
            return None
    retro = run_retrospective(store_dir, window=window)
    retro["trigger"] = "manual" if not force else "force"
    persist_retrospective(store_dir, retro)
    return retro


def retro_panel(store_dir: Path) -> dict[str, Any]:
    last = last_retrospective(store_dir)
    count = count_retrospectives(store_dir)
    return {
        "panel": "retrospective",
        "storage": "agent_journal.db",
        "ok": bool(last.get("try")),
        "runs": count,
        "last_at": last.get("at"),
        "keep_count": len(last.get("keep") or []),
        "stop_count": len(last.get("stop") or []),
        "try_count": len(last.get("try") or []),
        "last": last,
        "search_hint": "retrospective.try[].action, goal_id",
    }
