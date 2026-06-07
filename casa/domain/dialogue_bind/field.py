"""Field snapshot, capability, and recall cue helpers."""

from __future__ import annotations

import re
from typing import Any

from casa.domain.dialogue_bind.blocks import block_dict
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.sn_cen_runtime import TaskEmit
from casa.prisms.memory.memory_prisms import memory_lattices


def looks_like_field_recall(query: str) -> bool:
    ql = (query or "").lower()
    has_material_object = any(cue in ql for cue in ("палоч", "куч", "коров", "картинк"))
    if "на поле" not in ql and not has_material_object:
        return False
    return any(
        cue in ql
        for cue in (
            "ты видел",
            "что заметил",
            "опиши",
            "объясни",
            "скажи своими словами",
            "своими словами",
            "сравни",
            "сколько",
        )
    )


def salient_recall_tokens(query: str) -> list[str]:
    stop = frozenset(
        {
            "что",
            "это",
            "слово",
            "означает",
            "запомни",
            "как",
            "или",
            "нужна",
            "нужно",
            "верно",
            "правильно",
        }
    )
    toks = re.findall(r"[\w\u0400-\u04FF]+", query or "", flags=re.UNICODE)
    out = [t for t in toks if len(t) >= 5 and t.lower() not in stop]
    return list(dict.fromkeys(out))


def field_snapshot_block(state: dict, wm: WorkingMemory) -> dict[str, Any]:
    fv = int(state.get("field_version") or 0)
    goal = (wm.goal_id or wm.goal or "").strip()
    active = ""
    mem = memory_lattices(state)
    if mem:
        from casa.domain.prism_wire import prism_memory

        active = str(prism_memory(state).get("active_lattice") or next(iter(mem.keys()), ""))
    parts = [f"field_version {fv}", f"tick {wm.tick}"]
    if goal:
        parts.append(f"goal {goal[:80]}")
    if active:
        parts.append(f"active_lattice {active}")
    return block_dict(
        "subject.field.snapshot",
        "; ".join(parts) + ".",
        source="field",
        score=9,
    )


def capability_block(state: dict, wm: WorkingMemory, task: TaskEmit | None) -> dict[str, Any]:
    caps: list[str] = []
    subject = state.get("subject")
    if isinstance(subject, dict):
        disp = subject.get("last_disposition")
        if isinstance(disp, dict) and disp.get("action"):
            caps.append(f"agency:{disp['action']}")
    if wm.step_capability:
        caps.append(str(wm.step_capability))
    if task and task.concepts:
        caps.extend(str(c) for c in task.concepts[:3] if not str(c).startswith("module:"))
    if not caps:
        caps = ["literacy RU/EN", "dialogue", "autonomy", "field memory"]
    return block_dict(
        "subject.self.capability",
        "На поле веду: " + ", ".join(dict.fromkeys(caps)) + ".",
        source="field",
        score=11,
    )
