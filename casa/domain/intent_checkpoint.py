#!/usr/bin/env python3
"""Intent checkpoint — WM survives interrupt (ADR-0036)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from casa.prisms.control.fpn_state import SESSION_NAME, WorkingMemory

DEFAULT_RESTORE_TTL_TICKS = 48


def _read_session(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def save_intent_checkpoint(
    store_dir: Path,
    wm: WorkingMemory,
    *,
    why: str,
    tick: int | None = None,
) -> dict[str, Any]:
    path = store_dir.resolve() / SESSION_NAME
    session = _read_session(path)
    ck = {
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tick": tick if tick is not None else wm.tick,
        "why": str(why or "macro_tick")[:200],
        "wm": wm.to_dict(),
    }
    session["intent_checkpoint"] = ck
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
    return ck


def load_intent_checkpoint(store_dir: Path) -> dict[str, Any] | None:
    ck = _read_session(store_dir.resolve() / SESSION_NAME).get("intent_checkpoint")
    return ck if isinstance(ck, dict) else None


def checkpoint_restore_candidate(
    store_dir: Path,
    wm: WorkingMemory,
) -> dict[str, Any] | None:
    """Proposal for arbiter when WM empty and checkpoint fresh."""
    if wm.goal_id or wm.goal.strip():
        return None
    ck = load_intent_checkpoint(store_dir)
    if not ck:
        return None
    saved_tick = int(ck.get("tick") or 0)
    if wm.tick - saved_tick > DEFAULT_RESTORE_TTL_TICKS:
        return None
    saved_wm = ck.get("wm") if isinstance(ck.get("wm"), dict) else {}
    if not saved_wm.get("goal_id") and not saved_wm.get("goal"):
        return None
    return {
        "kind": "checkpoint",
        "goal_id": str(saved_wm.get("goal_id") or ""),
        "goal": str(saved_wm.get("goal") or ""),
        "step_capability": str(saved_wm.get("step_capability") or ""),
        "step_focus": str(saved_wm.get("step_focus") or ""),
        "why": ck.get("why"),
        "saved_tick": saved_tick,
    }


def apply_checkpoint_to_wm(wm: WorkingMemory, proposal: dict[str, Any]) -> None:
    if proposal.get("goal_id"):
        wm.goal_id = str(proposal["goal_id"])
    if proposal.get("goal"):
        wm.goal = str(proposal["goal"])
    if proposal.get("step_capability"):
        wm.step_capability = str(proposal["step_capability"])
    if proposal.get("step_focus"):
        wm.step_focus = str(proposal["step_focus"])
    wm.subgoal = "checkpoint_restore"
