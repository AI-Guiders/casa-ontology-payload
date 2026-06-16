"""Buffer compose-time impulse events until partner-dialogue channel opens."""

from __future__ import annotations

from typing import Any

from casa.nervous.impulse import impulse_recorder

_META_KEY = "impulse_compose_pending"


def record_compose_select(
    state: dict | None,
    node: str,
    *,
    zone: str = "",
    selected: list[str] | None = None,
    potentials: list[dict[str, Any]] | None = None,
    inputs: dict[str, Any] | None = None,
    rejected_above_floor: int = 0,
) -> None:
    if not state or not impulse_recorder().is_active:
        return
    meta = state.setdefault("meta", {})
    pending: list[dict[str, Any]] = meta.setdefault(_META_KEY, [])
    pending.append(
        {
            "node": node,
            "zone": zone,
            "selected": list(selected or []),
            "potentials": list(potentials or []),
            "inputs": dict(inputs or {}),
            "rejected_above_floor": max(0, int(rejected_above_floor)),
        }
    )


def flush_compose_pending(state: dict | None, imp: Any) -> None:
    if not state:
        return
    meta = state.get("meta")
    if not isinstance(meta, dict):
        return
    pending = meta.pop(_META_KEY, None)
    if not pending:
        return
    for row in pending:
        if not isinstance(row, dict):
            continue
        imp.select(
            str(row.get("node") or "compose"),
            zone=str(row.get("zone") or ""),
            selected=list(row.get("selected") or []),
            potentials=list(row.get("potentials") or []),
            inputs=dict(row.get("inputs") or {}),
            rejected_above_floor=int(row.get("rejected_above_floor") or 0),
        )


def set_discourse_affect_select(state: dict | None, register: str | None) -> None:
    if not state:
        return
    meta = state.setdefault("meta", {})
    if register:
        meta["discourse_affect_select"] = str(register)
    else:
        meta.pop("discourse_affect_select", None)


def pop_discourse_affect_select(state: dict | None) -> str | None:
    if not state:
        return None
    meta = state.get("meta")
    if not isinstance(meta, dict):
        return None
    raw = meta.pop("discourse_affect_select", None)
    return str(raw).strip() if raw else None
