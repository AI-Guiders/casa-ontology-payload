#!/usr/bin/env python3
"""Wire-format prism tree: normalize, kind inference, system bootstrap (ADR-0020 M4)."""

from __future__ import annotations

from typing import Any

from casa.domain.prism_ids import (
    PRISM_AGENT,
    PRISM_CONTROL,
    PRISM_HIPPO,
    PRISM_HOT_CONTEXT,
    PRISM_KIND_CONTENT,
    PRISM_KIND_CONTROL,
    PRISM_KIND_HIPPO,
    PRISM_KIND_HOT_CONTEXT,
    PRISM_KIND_ROUTER,
    PRISM_MEMORY,
    PRISM_ROUTER,
    ROOT,
    SCHEMA_CURRENT,
    SN_ACTIVE_CONTROL,
    SN_ACTIVE_PRISM,
)
from casa.prisms.shared.lattice_names_v1 import ALPHABET_RU, CONTROL_DMN


def infer_prism_kind(prism_id: str, block: dict[str, Any] | None) -> str:
    """Single source for kind from wire block + id heuristics."""
    block = block or {}
    explicit = block.get("kind")
    if explicit:
        return str(explicit)
    if prism_id == PRISM_HOT_CONTEXT:
        return PRISM_KIND_HOT_CONTEXT
    if prism_id == PRISM_ROUTER:
        return PRISM_KIND_ROUTER
    if prism_id == PRISM_CONTROL:
        return PRISM_KIND_CONTROL
    if prism_id in (PRISM_HIPPO,) or prism_id.endswith("_hippo"):
        return PRISM_KIND_HIPPO
    return PRISM_KIND_CONTENT


def prism_supports_lattices_for(
    prism_id: str,
    *,
    kind: str | None = None,
    block: dict[str, Any] | None = None,
) -> bool:
    """True when prism exports content/control lattices (not hot/router/hippo)."""
    k = kind if kind is not None else infer_prism_kind(prism_id, block)
    if prism_id in (PRISM_HIPPO, PRISM_AGENT, PRISM_HOT_CONTEXT, PRISM_ROUTER):
        return False
    if prism_id == PRISM_CONTROL:
        return False
    if k in (PRISM_KIND_HOT_CONTEXT, PRISM_KIND_ROUTER, PRISM_KIND_HIPPO):
        return False
    if k in (PRISM_KIND_CONTENT, PRISM_KIND_CONTROL):
        return True
    return isinstance((block or {}).get("lattices"), dict)


def normalize_prisms(state: dict) -> dict:
    """Ensure wire has prisms root and current schema (idempotent)."""
    state.setdefault(ROOT, {})
    if not state.get("schema_version"):
        state["schema_version"] = SCHEMA_CURRENT
    return state


def prisms(state: dict) -> dict[str, Any]:
    normalize_prisms(state)
    return state.setdefault(ROOT, {})


def _ensure_block(state: dict, prism_id: str, factory: dict[str, Any]) -> dict[str, Any]:
    root = prisms(state)
    if prism_id not in root:
        root[prism_id] = dict(factory)
    return root[prism_id]


def prism_memory(state: dict) -> dict[str, Any]:
    return _ensure_block(
        state,
        PRISM_MEMORY,
        {
            "subsystem": "sss",
            "stack": "design/prisms/memory/stack.json",
            "lattices": {},
            "active_lattice": ALPHABET_RU,
        },
    )


def prism_hippo(state: dict) -> dict[str, Any]:
    return _ensure_block(
        state,
        PRISM_HIPPO,
        {"subsystem": "episodic", "lattices": {}, "episodes": []},
    )


def prism_control(state: dict) -> dict[str, Any]:
    return _ensure_block(
        state,
        PRISM_CONTROL,
        {
            "subsystem": "control",
            "stack": "design/control-lattice-stack.json",
            "lattices": {},
            "active_lattice": CONTROL_DMN,
        },
    )


def prism_agent(state: dict) -> dict[str, Any]:
    return _ensure_block(
        state,
        PRISM_AGENT,
        {
            "subsystem": "agent_owned",
            "kind": PRISM_KIND_CONTENT,
            "lattices": {},
            "active_lattice": None,
            "nca": {"models": {}},
        },
    )


def prism_hot_context(state: dict) -> dict[str, Any]:
    return _ensure_block(
        state,
        PRISM_HOT_CONTEXT,
        {
            "kind": PRISM_KIND_HOT_CONTEXT,
            "schema_version": 1,
            "stack": "design/prisms/hot_context/stack.json",
            "edges": [],
            "max_edges": 4096,
        },
    )


def prism_router(state: dict) -> dict[str, Any]:
    return _ensure_block(
        state,
        PRISM_ROUTER,
        {
            "kind": PRISM_KIND_ROUTER,
            "schema_version": 1,
            "stack": "design/prisms/router/stack.json",
            "default_content_prism": PRISM_MEMORY,
            "routes": [],
        },
    )


def prism_block(state: dict, prism_id: str) -> dict[str, Any]:
    """Return prism block; does not create empty shells (use system ensure_* or spawn)."""
    normalize_prisms(state)
    block = prisms(state).get(prism_id)
    if isinstance(block, dict):
        return block
    return prisms(state).setdefault(prism_id, {})


def prism_kind(state: dict, prism_id: str) -> str:
    return infer_prism_kind(prism_id, prism_block(state, prism_id))


def prism_supports_lattices(state: dict, prism_id: str) -> bool:
    block = prism_block(state, prism_id)
    return prism_supports_lattices_for(prism_id, block=block)


def active_control_prism_id(state: dict, *, default: str = PRISM_CONTROL) -> str:
    sn = state.get("sn") or {}
    return str(sn.get(SN_ACTIVE_CONTROL) or default)


def set_active_control_prism(state: dict, prism_id: str) -> None:
    state["sn"] = {**(state.get("sn") or {}), SN_ACTIVE_CONTROL: prism_id}


def active_prism_id(state: dict, *, default: str = PRISM_MEMORY) -> str:
    sn = state.get("sn") or {}
    return str(sn.get(SN_ACTIVE_PRISM) or default)


def set_active_prism(state: dict, prism_id: str) -> None:
    state["sn"] = {**(state.get("sn") or {}), SN_ACTIVE_PRISM: prism_id}
