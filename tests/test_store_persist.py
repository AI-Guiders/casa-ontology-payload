"""Runtime persist — runtime checkpoint tier (field_state + self/agent)."""

from __future__ import annotations

import json
from pathlib import Path

from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.shared.store_layout import (
    STORE_TIER_RUNTIME,
    STORE_TIER_SHIPPED,
    field_state_path,
    runtime_checkpoint_paths,
    shipped_tier_roots,
    self_tier_roots,
)
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state


def test_store_tier_constants() -> None:
    assert STORE_TIER_SHIPPED == "shipped"
    assert STORE_TIER_RUNTIME == "runtime"


def test_runtime_checkpoint_paths(tmp_path: Path) -> None:
    paths = runtime_checkpoint_paths(tmp_path)
    assert paths["field_state"].name == "field_state.json"
    assert paths["agent_session"].name == "agent_session.json"


def test_save_runtime_state_skips_unchanged(tmp_path: Path) -> None:
    store = tmp_path / "store"
    store.mkdir()
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 3})
    fv = int(state["field_version"])
    save_field_state(field_state_path(store), state)

    rep = save_runtime_state(store, state, baseline_version=fv)
    assert rep["saved"] is False
    assert rep["tier"] == STORE_TIER_RUNTIME


def test_save_runtime_state_writes_when_dirty(tmp_path: Path) -> None:
    store = tmp_path / "store"
    store.mkdir()
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 3})
    mark_runtime_dirty(state)
    state["sn"] = {"last_tick": 1}

    rep = save_runtime_state(store, state, baseline_version=3)
    assert rep["saved"] is True
    assert rep["tier"] == STORE_TIER_RUNTIME

    loaded = load_field_state(field_state_path(store))
    assert loaded.get("sn", {}).get("last_tick") == 1


def test_save_state_alias_uses_runtime_persist(tmp_path: Path) -> None:
    from casa.prisms.memory.memory_prisms import save_state

    store = tmp_path / "store"
    store.mkdir()
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    state["sn"] = {"mode": "wake"}
    save_state(field_state_path(store), state)

    loaded = json.loads(field_state_path(store).read_text(encoding="utf-8"))
    assert loaded["sn"]["mode"] == "wake"


def test_tier_path_helpers(tmp_path: Path) -> None:
    store = tmp_path / "store"
    store.mkdir()
    assert shipped_tier_roots(store)["ltm"].name == "ltm"
    assert self_tier_roots(store)["agent"].name == "agent"
