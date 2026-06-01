"""Agent-owned prism — lattices outside profile ltm/."""

from __future__ import annotations

from pathlib import Path

import pytest

from casa.prisms.memory.agent_prism import (
    create_agent_lattice,
    delete_agent_lattice,
    list_agent_lattices,
    load_agent_prism,
    place_agent_token,
    read_agent_lattice,
    safe_agent_lattice_id,
    save_agent_prism,
)
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.domain.prism_ids import PRISM_AGENT
from casa.domain.prism_wire import prism_agent


def test_lattice_id_prefix() -> None:
    assert safe_agent_lattice_id("agent-scratch-math") == "agent-scratch-math"
    with pytest.raises(ValueError):
        safe_agent_lattice_id("F0_schema")


def test_agent_prism_roundtrip(tmp_path: Path) -> None:
    store = tmp_path / "store"
    store.mkdir()
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})

    create_agent_lattice(state, "agent-scratch-math", width=16, height=16)
    place_agent_token(state, "agent-scratch-math", "M:qty:2×entity:stick", x=2, y=3)
    save_agent_prism(store, state)

    state2 = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    loaded = load_agent_prism(store, state2)
    assert loaded["loaded_lattices"] == ["agent-scratch-math"]
    assert len(list_agent_lattices(state2)) == 1
    dec = read_agent_lattice(state2, "agent-scratch-math")
    assert dec["token_count"] >= 1
    assert PRISM_AGENT in state2.get("prisms", {})
    assert prism_agent(state2)["active_lattice"] == "agent-scratch-math"

    assert delete_agent_lattice(state2, "agent-scratch-math") is True
    assert list_agent_lattices(state2) == []
