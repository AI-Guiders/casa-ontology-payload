#!/usr/bin/env python3
"""Persist **runtime checkpoint** tier after wake/tick/sleep.

Store tiers (canon — see design/memory-hierarchy.md § Store tiers):

| Tier | Name | Survives process restart | In profile tar |
|------|------|--------------------------|----------------|
| Shipped | profile pack | yes (cold boot) | yes |
| Runtime | checkpoint | yes (same store dir) | no |
| Self | agent-owned | yes (agent/, journal/) | no |
"""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from pathlib import Path
from typing import Any

from casa.prisms.shared.field_write import save_field_state
from casa.prisms.shared.store_layout import (
    STORE_TIER_RUNTIME,
    STORE_TIER_SELF,
    STORE_TIER_SHIPPED,
    agent_prism_root,
    field_state_path,
    runtime_checkpoint_paths,
)


def mark_runtime_dirty(state: dict) -> None:
    """Call after in-memory prism mutations that must survive process restart."""
    state["_runtime_dirty"] = True


def save_runtime_state(
    store_dir: Path,
    state: dict,
    *,
    baseline_version: int | None = None,
    force: bool = False,
    compact: bool | None = None,
    save_agent: bool = True,
) -> dict[str, Any]:
    """Flush runtime checkpoint tier (field_state + optional self/agent mirror)."""
    store_dir = store_dir.resolve()
    dirty = force or bool(state.pop("_runtime_dirty", False))
    fv = int(state.get("field_version") or 0)
    if not force and not dirty and baseline_version is not None and fv == baseline_version:
        return {
            "saved": False,
            "reason": "unchanged",
            "field_version": fv,
            "tier": STORE_TIER_RUNTIME,
        }

    if compact is None:
        compact = store_dir.name.startswith("sss-")

    checkpoints = runtime_checkpoint_paths(store_dir)
    fs = checkpoints["field_state"]
    save_field_state(fs, state, compact=compact)

    agent_saved = False
    if save_agent and agent_prism_root(store_dir).is_dir():
        from casa.prisms.memory.agent_prism import save_agent_prism

        save_agent_prism(store_dir, state)
        agent_saved = True

    return {
        "saved": True,
        "tier": STORE_TIER_RUNTIME,
        "field_state": str(fs),
        "field_version": fv,
        "compact": compact,
        "self_tier": {STORE_TIER_SELF: agent_saved},
    }


def load_runtime_state(store_dir: Path, *, prefer_field_state: bool = True) -> dict[str, Any]:
    """Load shipped profile via boot or resume runtime checkpoint + self tier."""
    from casa.prisms.memory.memory_prisms import ensure_prisms
    from casa.prisms.shared.field_write import load_field_state
    from casa.prisms.memory.agent_prism import load_agent_prism
    from casa.prisms.memory.agent_bridges import load_agent_bridges

    store_dir = store_dir.resolve()
    fs = field_state_path(store_dir)
    boot_source = STORE_TIER_RUNTIME if prefer_field_state and fs.is_file() else STORE_TIER_SHIPPED

    if prefer_field_state and fs.is_file():
        state = ensure_prisms(load_field_state(fs))
    else:
        from casa.prisms.shared.store_boot import boot_store

        boot = boot_store(store_dir, prefer_field_state=False)
        state = boot["state"]

    agent_load = None
    bridges_load = None
    if agent_prism_root(store_dir).is_dir():
        agent_load = load_agent_prism(store_dir, state)
        bridges_load = load_agent_bridges(store_dir, state)

    return {
        "state": state,
        "boot_source": boot_source,
        "field_version": state.get("field_version"),
        "agent_prism": agent_load,
        "agent_bridges": bridges_load,
    }
