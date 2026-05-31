"""Unified agent self-memory."""

from __future__ import annotations

from pathlib import Path

from casa.prisms.memory.agent_memory_ops import agent_recall, agent_remember
from casa.prisms.memory.memory_prisms import ensure_prisms


def test_remember_any_json(tmp_path: Path) -> None:
    store = tmp_path / "store"
    store.mkdir()
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})

    rep = agent_remember(
        store,
        state,
        {"data": {"lesson": "cow+cow", "n": 2}, "tags": ["math"]},
        scope="self",
    )
    assert rep["remembered"] is True

    got = agent_recall(store, tag="math")
    assert got["count"] == 1
    assert "cow+cow" in got["records"][0]["text"] or got["records"][0].get("meta")


def test_remember_text_and_tokens(tmp_path: Path) -> None:
    store = tmp_path / "store"
    store.mkdir()
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})

    rep = agent_remember(
        store,
        state,
        {"text": "noticed pattern", "tokens": ["M:custom:foo"], "concepts": ["custom.foo"]},
    )
    assert rep["field_placements"] >= 1

    got = agent_recall(store, concept="custom.foo")
    assert got["count"] == 1
