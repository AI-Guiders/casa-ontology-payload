#!/usr/bin/env python3
"""Prism block keys (square lattice stacks). Legacy cyl_* read + normalize on load."""

from __future__ import annotations

from typing import Any

SCHEMA_LEGACY = "multi_cylinder_v1"
SCHEMA_CURRENT = "multi_prism_v1"

ROOT_LEGACY = "cylinders"
ROOT = "prisms"

PRISM_MEMORY = "prism_memory"
PRISM_HIPPO = "prism_hippo"
PRISM_CONTROL = "prism_control"

_LEGACY_BLOCK = {
    "cyl_memory": PRISM_MEMORY,
    "cyl_hippo": PRISM_HIPPO,
    "cyl_control": PRISM_CONTROL,
}

_ACTIVE_LEGACY = "active_cylinder"
_ACTIVE = "active_prism"


def normalize_prisms(state: dict) -> dict:
    """Migrate cylinders/cyl_* → prisms/prism_* (idempotent)."""
    if ROOT_LEGACY in state and ROOT not in state:
        state[ROOT] = state.pop(ROOT_LEGACY)

    root = state.setdefault(ROOT, {})
    for old, new in _LEGACY_BLOCK.items():
        if old in root and new not in root:
            root[new] = root.pop(old)

    if state.get("schema_version") == SCHEMA_LEGACY:
        state["schema_version"] = SCHEMA_CURRENT

    sn = state.get("sn")
    if isinstance(sn, dict) and _ACTIVE_LEGACY in sn and _ACTIVE not in sn:
        raw = str(sn.pop(_ACTIVE_LEGACY))
        sn[_ACTIVE] = _LEGACY_BLOCK.get(raw, raw)
        state["sn"] = sn

    return state


def prisms(state: dict) -> dict[str, Any]:
    normalize_prisms(state)
    return state.setdefault(ROOT, {})


def prism_memory(state: dict) -> dict[str, Any]:
    p = prisms(state)
    if PRISM_MEMORY not in p:
        p[PRISM_MEMORY] = {
            "subsystem": "sss",
            "stack": "design/sss-lattice-stack.v0.json",
            "lattices": {},
            "active_lattice": "L0_grapheme_cyrl",
        }
    return p[PRISM_MEMORY]


def prism_hippo(state: dict) -> dict[str, Any]:
    p = prisms(state)
    if PRISM_HIPPO not in p:
        p[PRISM_HIPPO] = {"subsystem": "episodic", "lattices": {}, "episodes": []}
    return p[PRISM_HIPPO]


def prism_control(state: dict) -> dict[str, Any]:
    p = prisms(state)
    return p.setdefault(
        PRISM_CONTROL,
        {
            "subsystem": "control",
            "stack": "design/control-lattice-stack.v0.json",
            "lattices": {},
            "active_lattice": "lattice_dmn",
        },
    )


def active_prism_id(state: dict, *, default: str = PRISM_MEMORY) -> str:
    sn = state.get("sn") or {}
    return str(sn.get(_ACTIVE) or default)


def set_active_prism(state: dict, prism_id: str) -> None:
    state["sn"] = {**(state.get("sn") or {}), _ACTIVE: prism_id}
