#!/usr/bin/env python3
"""FPN working memory: agent_session.json + optional lattice_fpn_wm mirror."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SESSION_NAME = "agent_session.json"
JOURNAL_NAME = "agent_journal.db"


@dataclass
class WorkingMemory:
    mode: str = "explore"
    goal: str = ""
    goal_id: str = ""
    subgoal: str = ""
    tick: int = 0
    user_query: str = ""
    last_concepts: list[str] = field(default_factory=list)
    last_action: str = ""
    active_plan_id: str = ""
    plan_steps: list[str] = field(default_factory=list)
    step_index: int = 0
    step_capability: str = ""
    step_focus: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict | None) -> WorkingMemory:
        if not raw:
            return cls()
        return cls(
            mode=str(raw.get("mode") or "explore"),
            goal=str(raw.get("goal") or ""),
            goal_id=str(raw.get("goal_id") or ""),
            subgoal=str(raw.get("subgoal") or ""),
            tick=int(raw.get("tick") or 0),
            user_query=str(raw.get("user_query") or ""),
            last_concepts=list(raw.get("last_concepts") or []),
            last_action=str(raw.get("last_action") or ""),
            active_plan_id=str(raw.get("active_plan_id") or ""),
            plan_steps=list(raw.get("plan_steps") or []),
            step_index=int(raw.get("step_index") or 0),
            step_capability=str(raw.get("step_capability") or ""),
            step_focus=str(raw.get("step_focus") or ""),
        )


def session_path(store_dir: Path) -> Path:
    return store_dir.resolve() / SESSION_NAME


def load_session(store_dir: Path) -> WorkingMemory:
    path = session_path(store_dir)
    if not path.is_file():
        return WorkingMemory()
    raw = json.loads(path.read_text(encoding="utf-8"))
    wm = raw.get("wm") if isinstance(raw, dict) and "wm" in raw else raw
    return WorkingMemory.from_dict(wm if isinstance(wm, dict) else None)


def _compact_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def read_session_meta(store_dir: Path) -> dict[str, Any]:
    path = session_path(store_dir)
    if not path.is_file():
        return {"schema_version": 2, "journal": JOURNAL_NAME}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": 2, "journal": JOURNAL_NAME}
    return raw if isinstance(raw, dict) else {"schema_version": 2, "journal": JOURNAL_NAME}


def write_session_meta(store_dir: Path, meta: dict[str, Any]) -> None:
    path = session_path(store_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(meta)
    payload.setdefault("schema_version", 2)
    payload.setdefault("journal", JOURNAL_NAME)
    path.write_text(_compact_json(payload) + "\n", encoding="utf-8")


def save_session(store_dir: Path, wm: WorkingMemory) -> None:
    meta = read_session_meta(store_dir)
    meta["schema_version"] = 2
    meta["journal"] = JOURNAL_NAME
    meta["wm"] = wm.to_dict()
    write_session_meta(store_dir, meta)


def effective_user_query(wm: WorkingMemory | None, cli_query: str | None) -> str | None:
    if cli_query and cli_query.strip():
        return cli_query.strip()
    if wm and wm.user_query.strip():
        return wm.user_query.strip()
    if wm and wm.goal.strip():
        return wm.goal.strip()
    return None


def salience_mode_bias(
    wm: WorkingMemory | None,
    concept_ids: list[str],
) -> dict[str, float] | None:
    if wm is None:
        return None
    bias: dict[str, float] = {}
    boost = 0.12 if wm.mode == "execute" else 0.06
    for cid in wm.last_concepts:
        if cid in concept_ids:
            bias[cid] = boost
    if wm.goal:
        g = wm.goal.lower()
        for cid in concept_ids:
            tail = cid.split(".")[-1].lower()
            if tail and tail in g:
                bias[cid] = bias.get(cid, 0.0) + 0.08
    return bias or None


def fpn_after_cen(
    wm: WorkingMemory,
    task: Any,
    *,
    user_query: str | None = None,
) -> WorkingMemory:
    action = getattr(task, "action", None) or (task.get("action") if isinstance(task, dict) else "")
    intent = getattr(task, "intent", None) or (task.get("intent") if isinstance(task, dict) else "")
    concepts = list(getattr(task, "concepts", None) or (task.get("concepts") if isinstance(task, dict) else []) or [])
    return WorkingMemory(
        mode=wm.mode if wm.mode != "explore" else "execute",
        goal=wm.goal or str(intent or ""),
        goal_id=wm.goal_id,
        subgoal=str(action or wm.subgoal),
        tick=wm.tick + 1,
        user_query=user_query or wm.user_query,
        last_concepts=concepts[:8] or wm.last_concepts,
        last_action=str(action or ""),
        active_plan_id=wm.active_plan_id,
        plan_steps=list(wm.plan_steps),
        step_index=wm.step_index,
        step_capability=wm.step_capability,
        step_focus=wm.step_focus,
    )
