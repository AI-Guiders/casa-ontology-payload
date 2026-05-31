#!/usr/bin/env python3
"""Per-prism field_version counters (memory vs control); global field_version = max."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from typing import Any


def memory_field_version(state: dict[str, Any]) -> int:
    mem = state.get("memory") or {}
    if "field_version" in mem:
        return int(mem["field_version"])
    return int(state.get("field_version") or 0)


def control_field_version(state: dict[str, Any]) -> int:
    ctrl = state.get("control") or {}
    if "field_version" in ctrl:
        return int(ctrl["field_version"])
    return 0


def sync_global_field_version(state: dict[str, Any]) -> int:
    v = max(memory_field_version(state), control_field_version(state))
    state["field_version"] = v
    return v


def bump_memory_field_version(state: dict[str, Any]) -> int:
    mem = state.setdefault("memory", {})
    base = int(mem.get("field_version") or state.get("field_version") or 0)
    mem["field_version"] = base + 1
    return sync_global_field_version(state)


def bump_control_field_version(state: dict[str, Any]) -> int:
    ctrl = state.setdefault("control", {})
    base = int(ctrl.get("field_version") or 0)
    ctrl["field_version"] = base + 1
    return sync_global_field_version(state)


def train_field_version_for_lattice(state: dict[str, Any], lattice_id: str, *, is_memory: bool) -> int:
    if is_memory:
        return memory_field_version(state)
    return control_field_version(state) or int(state.get("field_version") or 0)
