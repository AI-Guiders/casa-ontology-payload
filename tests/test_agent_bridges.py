"""Agent-owned bridges — links from prism_agent to profile lattices."""

from __future__ import annotations

from pathlib import Path

import pytest

from casa.prisms.memory.agent_bridges import (
    add_agent_bridge,
    load_agent_bridges,
    merge_digest_with_agent_bridges,
    remove_agent_bridge,
    safe_bridge_id,
    save_agent_bridges,
)
from casa.prisms.memory.agent_prism import create_agent_lattice, load_agent_prism, save_agent_prism
from casa.prisms.control.sn_cen_runtime import digest_from_decoded
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.lattice_names_v1 import CONTROL_DMN
from casa.prisms.shared.prism_state import PRISM_CONTROL, prism_control
from casa.prisms.shared.store_layout import agent_bridges_path


def test_bridge_id_prefix() -> None:
    assert safe_bridge_id("ab-agent-control-to-dmn") == "ab-agent-control-to-dmn"
    with pytest.raises(ValueError):
        safe_bridge_id("z_bridge_L0_L1")


def test_agent_bridge_roundtrip(tmp_path: Path) -> None:
    store = tmp_path / "store"
    store.mkdir()
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    prism_control(state)["lattices"].setdefault(CONTROL_DMN, {"cells": [], "width": 8, "height": 8})
    create_agent_lattice(state, "agent-control-routing", width=8, height=8)

    record = add_agent_bridge(
        state,
        from_lattice="agent-control-routing",
        to_prism=PRISM_CONTROL,
        to_lattice=CONTROL_DMN,
        relation="routes_to",
        tokens=["E:agent.control.routing|denotes|control.dmn"],
    )
    assert record["id"].startswith("ab-")
    save_agent_bridges(store, state)
    save_agent_prism(store, state)

    assert agent_bridges_path(store).is_file()

    state2 = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    prism_control(state2)["lattices"].setdefault(CONTROL_DMN, {"cells": [], "width": 8, "height": 8})
    load_agent_prism(store, state2)
    loaded = load_agent_bridges(store, state2)
    assert loaded["loaded"] == 1
    assert remove_agent_bridge(state2, record["id"]) is True
    save_agent_bridges(store, state2)
    assert load_agent_bridges(store, state2)["loaded"] == 0


def test_merge_digest_with_bridges() -> None:
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    prism_control(state)["lattices"].setdefault(CONTROL_DMN, {"cells": [], "width": 8, "height": 8})
    create_agent_lattice(state, "agent-control-routing", width=8, height=8)
    add_agent_bridge(
        state,
        from_lattice="agent-control-routing",
        to_prism=PRISM_CONTROL,
        to_lattice=CONTROL_DMN,
        tokens=["E:agent.control.routing|denotes|control.dmn"],
    )
    base = digest_from_decoded({"concept_ids": [], "edges": []})
    merged = merge_digest_with_agent_bridges(base, state)
    assert "control.dmn" in merged.concept_ids
    assert CONTROL_DMN in merged.concept_ids
    assert any(t.startswith("E:") for t in merged.edge_tokens)
    assert any(m.startswith("agent_bridge:") for m in merged.modules_active)
