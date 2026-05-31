#!/usr/bin/env python3
"""prism_control: DMN / SN / FPN / CEN lattice stack."""

from __future__ import annotations

from prism_state_v0 import PRISM_CONTROL, normalize_prisms, prism_control  # type: ignore
from pathlib import Path
from typing import Any

from control_stack_v0 import (  # type: ignore
    DEFAULT_STACK,
    encode_control_stack,
    load_control_stack,
    migrate_legacy_grid_to_control,
)
from field_version_v0 import bump_control_field_version  # type: ignore
from lattice_names_v1 import has_control_lattice, legacy_to_v1  # type: ignore
from sss_cylinders_v0 import ensure_cylinders  # type: ignore


def has_control_stack(state: dict) -> bool:
    normalize_prisms(state)
    lats = prism_control(state).get("lattices") or {}
    return has_control_lattice(lats)


def control_lattices(state: dict) -> dict[str, dict]:
    state = ensure_control_cylinder(state)
    return dict(prism_control(state).get("lattices") or {})


def ensure_control_cylinder(state: dict, *, stack_path: str | Path | None = None) -> dict:
    state = ensure_cylinders(state)
    normalize_prisms(state)
    stack_ref = str(stack_path or DEFAULT_STACK)
    ctrl = prism_control(state)
    if ctrl.get("lattices"):
        if not ctrl.get("stack"):
            ctrl["stack"] = stack_ref
        return state

    stack = load_control_stack(Path(stack_ref))
    lattices: dict[str, dict] = {}
    for lat in stack.get("lattices") or []:
        from control_stack_v0 import empty_control_lattice  # type: ignore

        lattices[str(lat["id"])] = empty_control_lattice(lat)

    ctrl["subsystem"] = "control"
    ctrl["stack"] = stack_ref
    ctrl["lattices"] = lattices
    ctrl["active_lattice"] = legacy_to_v1("lattice_dmn")
    state.setdefault("control", {})["stack_version"] = int(stack.get("schema_version") or 1)
    return state


ensure_control_prism = ensure_control_cylinder


def migrate_control_stack(
    state: dict,
    bundle: dict | None = None,
    *,
    layout: dict | None = None,
    copies: int = 5,
    stack_path: str | Path | None = None,
    wm_mode: str = "explore",
    wm_goal: str = "",
) -> dict[str, Any]:
    """Populate prism_control from bundle (preferred) or legacy 64² grid."""
    state = ensure_control_cylinder(state, stack_path=stack_path)
    stack = load_control_stack(Path(stack_path) if stack_path else None)

    if bundle is not None:
        lattices = encode_control_stack(bundle, stack, copies=copies, wm_mode=wm_mode, wm_goal=wm_goal)
        source = "bundle"
    elif state.get("grid") and layout is not None:
        lattices = migrate_legacy_grid_to_control(state["grid"], layout, stack)
        source = "legacy_grid"
    else:
        lattices = encode_control_stack(
            {"claims": [], "graph": {"edges": []}},
            stack,
            copies=copies,
            wm_mode=wm_mode,
            wm_goal=wm_goal,
        )
        source = "seed_only"

    ctrl = prism_control(state)
    ctrl["lattices"] = lattices
    state["control"] = {
        **(state.get("control") or {}),
        "migrated": True,
        "migrate_source": source,
        "stack": str(stack_path or DEFAULT_STACK),
        "lattice_ids": sorted(lattices.keys()),
    }
    bump_control_field_version(state)
    normalize_prisms(state)
    return {
        "source": source,
        "lattice_ids": sorted(lattices.keys()),
        "token_counts": {lid: _token_count(lat) for lid, lat in lattices.items()},
    }


def _token_count(lat: dict) -> int:
    return sum(len(cell) for cell in lat.get("cells") or [])
