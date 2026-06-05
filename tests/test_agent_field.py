#!/usr/bin/env python3
"""ADR-0039 agent_field.db tests."""

from __future__ import annotations

import json
from pathlib import Path

from casa.domain.agent_field import (
    FIELD_DB_NAME,
    field_db_path,
    import_field_from_json,
    load_field_from_db,
    save_field_to_db,
)
from casa.domain.routing import ROUTE_KIND_KNOWLEDGE, Router
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.field_write import load_field_state, save_field_state
from casa.prisms.shared.store_layout import field_state_path


def _minimal_state() -> dict:
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 1})
    Router.bind(state).bootstrap_defaults(locale="ru")
    Router.bind(state).add_route(
        {"goal": "goal.test"},
        route_kind="applicability",
        target_plan="plan.test",
        steps=["skill.read.analytic"],
        priority=10,
    )
    state["sn"] = {"mode": "wake"}
    return state


def test_save_load_field_db_roundtrip(tmp_path: Path):
    store = tmp_path / "agent"
    store.mkdir()
    state = _minimal_state()
    save_field_to_db(store, state)
    assert field_db_path(store).is_file()
    loaded = load_field_from_db(store)
    assert loaded is not None
    assert loaded.get("field_version") == state.get("field_version")
    routes = Router.bind(loaded).routes(route_kind=ROUTE_KIND_KNOWLEDGE)
    assert len(routes) >= 1
    app = Router.bind(loaded).routes(route_kind="applicability")  # type: ignore[arg-type]
    assert any(r.target_plan == "plan.test" for r in app)


def test_field_write_dual_write(tmp_path: Path):
    store = tmp_path / "agent"
    store.mkdir()
    state = _minimal_state()
    path = field_state_path(store)
    save_field_state(path, state, compact=True)
    assert path.is_file()
    assert field_db_path(store).is_file()
    loaded = load_field_state(path, store_dir=store)
    assert Router.bind(loaded).routes()


def test_import_from_json(tmp_path: Path):
    store = tmp_path / "agent"
    store.mkdir()
    state = _minimal_state()
    json_path = store / "field_state.json"
    json_path.write_text(json.dumps(state), encoding="utf-8")
    rep = import_field_from_json(store, json_path)
    assert rep.get("routes", 0) >= 1
    assert (store / FIELD_DB_NAME).is_file()
