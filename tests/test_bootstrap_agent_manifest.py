"""Declarative agent bootstrap manifest (Self tier + WM prism)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from casa.prisms.memory.agent_prism import agent_lattices
from casa.prisms.memory.bootstrap_agent_manifest import (
    bootstrap_agent_from_manifest,
    default_manifest_path,
    load_agent_bootstrap_manifest,
)
from casa.prisms.memory.wm import DEFAULT_SCRATCH_LATTICE, get_wm_policy
from casa.prisms.shared.store_boot import boot_store


def test_default_manifest_loads():
    manifest = load_agent_bootstrap_manifest()
    assert manifest["schema_version"] == 1
    wm = manifest["agent_prisms"]["wm_prism"]
    assert wm["enabled"] is True
    assert wm["scratch_lattice_id"] == "agent-wm-scratch"


def test_default_manifest_path_exists():
    path = default_manifest_path()
    assert path.is_file()
    assert path.name == "agent-bootstrap-manifest.v1.json"


def test_bootstrap_self_tier_and_wm_prism(tmp_path: Path):
    store_dir = tmp_path / "agent-test"
    store_dir.mkdir()
    (store_dir / "field").mkdir()
    (store_dir / "field" / "state.json").write_text(json.dumps({"tick": 0}), encoding="utf-8")

    manifest = load_agent_bootstrap_manifest()
    boot = boot_store(store_dir, prefer_field_state=True)
    state = boot["state"]

    rep = bootstrap_agent_from_manifest(
        store_dir,
        state,
        manifest,
        display_name="Тест",
    )

    assert rep["agent_prisms"]
    prism_ids = [row["prism"] for row in rep["agent_prisms"]]
    assert "wm_prism" in prism_ids
    assert "intent_prism" in prism_ids
    wm_row = next(r for r in rep["agent_prisms"] if r["prism"] == "wm_prism")
    assert wm_row["lattice_id"] == DEFAULT_SCRATCH_LATTICE

    from casa.prisms.memory.intent import DEFAULT_INTENT_LATTICE, get_intent_policy

    intent_row = next(r for r in rep["agent_prisms"] if r["prism"] == "intent_prism")
    assert intent_row["lattice_id"] == DEFAULT_INTENT_LATTICE

    lattices = agent_lattices(state)
    assert DEFAULT_SCRATCH_LATTICE in lattices
    assert "agent-self-default" in lattices
    assert DEFAULT_INTENT_LATTICE in lattices

    policy = get_wm_policy(state)
    assert policy["theta_hold"] == pytest.approx(0.45)
    assert get_intent_policy(state)["theta_promote"] == pytest.approx(0.62)

    journal = store_dir / "journal" / "self" / "entries.jsonl"
    assert journal.is_file()
    text = journal.read_text(encoding="utf-8")
    assert "Тест" in text
