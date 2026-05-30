#!/usr/bin/env python3
"""FPN working-memory session (v0) — file-backed; mirrors future grid wm.* channels."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sn_cen_runtime import TaskEmit  # type: ignore


@dataclass
class WmState:
    tick: int = 0
    goal: str = ""
    mode: str = "dialogue"  # dialogue | kb_query | code_nav | repair_field
    stack: list[str] = field(default_factory=list)
    last_action: str = ""
    last_query: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "goal": self.goal,
            "mode": self.mode,
            "stack": list(self.stack),
            "last_action": self.last_action,
            "last_query": self.last_query,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> WmState:
        if not data:
            return cls()
        return cls(
            tick=int(data.get("tick") or 0),
            goal=str(data.get("goal") or ""),
            mode=str(data.get("mode") or "dialogue"),
            stack=[str(x) for x in (data.get("stack") or [])],
            last_action=str(data.get("last_action") or ""),
            last_query=str(data.get("last_query") or ""),
        )


def session_path(store_dir: Path) -> Path:
    return store_dir / "agent_session.json"


def load_session(store_dir: Path) -> WmState:
    path = session_path(store_dir)
    if not path.is_file():
        return WmState()
    data = json.loads(path.read_text(encoding="utf-8"))
    return WmState.from_dict(data.get("wm"))


def save_session(store_dir: Path, wm: WmState, *, extra: dict[str, Any] | None = None) -> Path:
    path = session_path(store_dir)
    doc = {
        "schema_version": 1,
        "wm": wm.to_dict(),
        **(extra or {}),
    }
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def infer_mode_from_task(task: TaskEmit) -> str:
    if task.action in ("open_code",):
        return "code_nav"
    if task.action in ("open_kb", "answer_from_memory"):
        return "kb_query"
    if "repair" in (task.notes or "").lower():
        return "repair_field"
    return "dialogue"


def fpn_after_cen(
    wm: WmState,
    task: TaskEmit,
    *,
    user_query: str | None = None,
    set_goal_from_query: bool = True,
) -> WmState:
    """P4: CEN outcome → update WM for next tick T."""
    wm = WmState(
        tick=wm.tick + 1,
        goal=wm.goal,
        mode=infer_mode_from_task(task),
        stack=list(wm.stack),
        last_action=task.action,
        last_query=user_query or wm.last_query,
    )
    if user_query and set_goal_from_query:
        wm.goal = user_query.strip()[:240]
    elif not wm.goal and task.query_to_dmn:
        wm.goal = task.query_to_dmn[:240]
    if task.action == "query_to_dmn" or task.query_to_dmn:
        sub = (task.query_to_dmn or user_query or "")[:120]
        if sub and (not wm.stack or wm.stack[-1] != sub):
            wm.stack = (wm.stack + [sub])[-8:]
    return wm


def salience_mode_bias(wm: WmState, concept_ids: list[str]) -> dict[str, float]:
    """P5 stub: top-down boost by wm.mode."""
    bias: dict[str, float] = {}
    if wm.mode == "kb_query":
        for cid in concept_ids:
            if cid.startswith("ru.grammar.") or cid.startswith("ru.regex."):
                bias[cid] = 0.15
    elif wm.mode == "code_nav":
        for cid in concept_ids:
            if "code" in cid.lower():
                bias[cid] = 0.12
    return bias


def effective_user_query(wm: WmState, user_query: str | None) -> str | None:
    """Autonomous tick: reuse goal when no new external query."""
    if user_query and user_query.strip():
        return user_query.strip()
    if wm.goal.strip():
        return wm.goal.strip()
    return None
