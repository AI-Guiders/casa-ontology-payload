#!/usr/bin/env python3
"""Scoped bind — tract → memory domain lattice set (ADR-0068 P12b)."""

from __future__ import annotations

from typing import Any

from casa.prisms.intelligence.zone_prism_map import (
    lattices_for_scope,
    load_zone_prism_map,
    memory_resolve_scopes,
)
from casa.prisms.memory.zone import memory_kind_for_lattice


def _index_payload(state: dict) -> dict[str, Any]:
    idx = (state.get("meta") or {}).get("zone_lattice_index") or {}
    if not idx:
        return {"entries": []}
    return {
        "entries": [
            {"lattice_id": lid, **(tag if isinstance(tag, dict) else {})}
            for lid, tag in idx.items()
        ]
    }


def bind_scope(state: dict, *, tract: str, client_zone: str = "") -> dict[str, Any]:
    doc = load_zone_prism_map()
    return memory_resolve_scopes(
        doc,
        tract=str(tract or "general"),
        client_zone=client_zone,
        state=state,
    )


def scoped_lattice_ids(state: dict, scope: dict[str, Any]) -> set[str] | None:
    payload = _index_payload(state)
    if not payload["entries"]:
        return None
    return set(lattices_for_scope(payload, scope))


def apply_bind_scope(state: dict, *, tract: str, client_zone: str = "") -> dict[str, Any]:
    """Persist scope on state.meta for tick / field snapshot consumers."""
    from casa.prisms.memory.forgetting import memory_implicit_gains

    scope = bind_scope(state, tract=tract, client_zone=client_zone)
    allowed = scoped_lattice_ids(state, scope)
    gains = memory_implicit_gains(state, tract=tract)
    meta = state.setdefault("meta", {})
    meta["bind_scope"] = scope
    meta["bind_scope_lattices"] = sorted(allowed) if allowed is not None else []
    return {"scope": scope, "lattice_count": len(allowed or []), "implicit_gains": gains}


def lattice_allowed_for_bind(state: dict, lattice_id: str, scope: dict[str, Any]) -> bool:
    allowed = scoped_lattice_ids(state, scope)
    if allowed is None:
        return True
    lid = str(lattice_id)
    if lid in allowed:
        return True
    tag = memory_kind_for_lattice(state, lid)
    owner = str(tag.get("owner_zone") or "")
    if owner and owner != "memory":
        return True
    if not tag and lid.startswith("agent-"):
        return True
    if owner == "memory":
        return False
    return True


def filter_bind_blocks(
    blocks: list[dict[str, Any]],
    state: dict,
    *,
    intent: str,
) -> list[dict[str, Any]]:
    """Drop memory-owned lattice blocks outside tract scope when index present."""
    scope = bind_scope(state, tract=intent)
    if scoped_lattice_ids(state, scope) is None:
        return blocks
    out: list[dict[str, Any]] = []
    for row in blocks:
        slots = row.get("slots") if isinstance(row.get("slots"), dict) else {}
        lid = str(slots.get("lattice_id") or "")
        if lid and not lattice_allowed_for_bind(state, lid, scope):
            continue
        out.append(row)
    return out


def pick_scoped_active_lattice(state: dict, *, tract: str = "general") -> str:
    """Prefer active LTM lattice within bind scope."""
    from casa.domain.prism_wire import prism_memory
    from casa.prisms.memory.memory_prisms import memory_lattices

    mem = memory_lattices(state)
    if not mem:
        return ""
    scope = (state.get("meta") or {}).get("bind_scope") or bind_scope(state, tract=tract)
    allowed = scoped_lattice_ids(state, scope)
    candidates = [str(prism_memory(state).get("active_lattice") or "")]
    candidates.extend(sorted(mem.keys()))
    for lid in candidates:
        if not lid:
            continue
        if allowed is None or lid in allowed:
            return lid
    return ""


def constrain_lattice_hint(state: dict, hint: str | None, *, tract: str = "general") -> str | None:
    """Route hint must fall inside bind scope when index is wired."""
    if not hint:
        return hint
    scope = bind_scope(state, tract=tract)
    if lattice_allowed_for_bind(state, str(hint), scope):
        return hint
    allowed = scoped_lattice_ids(state, scope)
    if not allowed:
        return hint
    for lid in sorted(allowed):
        if lid.startswith(str(hint)) or str(hint) in lid:
            return lid
    return None
