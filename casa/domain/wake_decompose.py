#!/usr/bin/env python3
"""Wake decompose — phrase/word queue from event registry (ADR-0035 B7)."""

from __future__ import annotations

from typing import Any

from casa.domain.plan_tick import PlanTick
from casa.prisms.visual.phrase_compose import (
    load_phrase_events,
    phrase_compose_slice,
    phrase_probe_frame_id,
)

_DEFAULT_EVENT_ID = "lang.event.transitive.wash.v0"


def phrase_event_id_from_goal(goal_id: str) -> str:
    """Parse event from goal.read.phrase#lang.event.* suffix."""
    gid = str(goal_id or "").strip()
    if "#" in gid:
        return gid.split("#", 1)[1].strip()
    return _DEFAULT_EVENT_ID


def phrase_entry_for_goal(goal_id: str, *, events_path: str | None = None) -> dict[str, Any]:
    eid = phrase_event_id_from_goal(goal_id)
    for entry in load_phrase_events(events_path):
        if str(entry.get("event_id") or "") == eid:
            return entry
    entries = load_phrase_events(events_path)
    return entries[0] if entries else {}


def phrase_compose_entry_for_goal(goal_id: str, *, events_path: str | None = None) -> dict[str, Any]:
    return phrase_compose_slice(phrase_entry_for_goal(goal_id, events_path=events_path))


def _decompose_state(state: dict) -> dict[str, Any]:
    raw = state.setdefault("wake_decompose", {})
    return raw if isinstance(raw, dict) else {}


def phrase_words_for_goal(goal_id: str, *, events_path: str | None = None) -> list[dict[str, Any]]:
    """Words from phrase event registry for goal.read.phrase*."""
    gid = str(goal_id or "").strip()
    if not gid.startswith("goal.read.phrase"):
        return []
    entry = phrase_compose_entry_for_goal(gid, events_path=events_path)
    words = entry.get("words")
    if isinstance(words, list) and words:
        return [w for w in words if isinstance(w, dict) and w.get("surface")]
    return []


def init_phrase_queue(state: dict, goal_id: str) -> list[dict[str, Any]]:
    words = phrase_words_for_goal(goal_id)
    if not words:
        return []
    dec = _decompose_state(state)
    dec["goal_id"] = goal_id
    dec["event_id"] = phrase_event_id_from_goal(goal_id)
    dec["words"] = [
        {
            "surface": str(w.get("surface") or ""),
            "slug": str(w.get("slug") or ""),
            "frame_id": phrase_probe_frame_id(str(w.get("slug") or "")),
        }
        for w in words
    ]
    dec["word_index"] = 0
    state["wake_decompose"] = dec
    return dec["words"]


def current_word_focus(state: dict, *, goal_id: str = "") -> str:
    dec = _decompose_state(state)
    if goal_id and dec.get("goal_id") != goal_id:
        init_phrase_queue(state, goal_id)
        dec = _decompose_state(state)
    words = dec.get("words")
    if not isinstance(words, list) or not words:
        return ""
    idx = int(dec.get("word_index") or 0)
    if idx < 0 or idx >= len(words):
        return ""
    row = words[idx]
    return str(row.get("frame_id") or "") if isinstance(row, dict) else ""


def advance_word_queue(state: dict, *, passed: bool = True) -> dict[str, Any]:
    dec = _decompose_state(state)
    words = dec.get("words")
    if not isinstance(words, list) or not words:
        return {"advanced": False, "reason": "no_queue"}
    idx = int(dec.get("word_index") or 0)
    if passed and idx < len(words) - 1:
        dec["word_index"] = idx + 1
        state["wake_decompose"] = dec
        gid = str(dec.get("goal_id") or "")
        return {
            "advanced": True,
            "word_index": idx + 1,
            "frame_id": current_word_focus(state, goal_id=gid),
        }
    return {
        "advanced": False,
        "word_index": idx,
        "complete": passed and idx >= len(words) - 1,
    }


def apply_wake_decompose(state: dict, plan: PlanTick) -> PlanTick:
    """Set step_focus per word when executing analytic read on phrase goal."""
    gid = str(plan.goal_id or "").strip()
    if not gid.startswith("goal.read.phrase"):
        return plan
    cap = str(plan.step_capability or "").strip()
    if cap not in ("skill.read.analytic", "skill.verify.lex", ""):
        return plan
    if not cap:
        plan.step_capability = "skill.read.analytic"
        plan.sync_step_from_plan()
    focus = current_word_focus(state, goal_id=gid)
    if not focus:
        init_phrase_queue(state, gid)
        focus = current_word_focus(state, goal_id=gid)
    if focus and not plan.step_focus:
        out = PlanTick(
            goal_id=plan.goal_id,
            active_plan_id=plan.active_plan_id,
            plan_steps=list(plan.plan_steps),
            step_index=plan.step_index,
            step_capability=plan.step_capability or "skill.read.analytic",
            step_focus=focus,
        )
        out.sync_step_from_plan()
        return out
    return plan
