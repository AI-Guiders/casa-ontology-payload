#!/usr/bin/env python3
"""Consistency oracle + router boot probe tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from casa.domain.agent_field import save_field_to_db
from casa.domain.consistency_oracle import (
    apply_repair_homeostasis,
    assess_field_consistency,
)
from casa.domain.prism_ids import PRISM_LANG_RU
from casa.domain.router_boot_probe import run_router_boot_probe
from casa.domain.routing import ROUTE_KIND_KNOWLEDGE, Router
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.store_boot import boot_store


def test_consistency_ok_when_db_matches_state(tmp_path: Path):
    store = tmp_path / "agent-test"
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 9, "store": {"store_id": "agent-test"}})
    save_field_to_db(store, state)
    from casa.domain.agent_field import load_field_from_db

    loaded = load_field_from_db(store)
    assert loaded is not None

    report = assess_field_consistency(store, loaded)
    assert report["ok"] is True


def test_consistency_mismatch_triggers_repair_signal():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 10, "store": {"store_id": "t"}})
    report = {
        "repair_recommended": True,
        "mismatches": ["field_db:9_vs_state:10"],
    }
    out = apply_repair_homeostasis(state, report)
    assert out["applied"] is True
    assert state["sn"]["surprise"] >= 100
    assert state["consolidation"]["repair_pending"] is True


def test_router_boot_probe_resolves_knowledge(tmp_path: Path):
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 1, "store": {"store_id": "t"}})
    Router.bind(state).add_route({"modality": "t9", "locale": "ru"}, PRISM_LANG_RU, route_kind=ROUTE_KIND_KNOWLEDGE)

    probe = run_router_boot_probe(state, store_dir=tmp_path)
    assert probe["ok"] is True
    assert "knowledge_t9_ru" not in probe["required_failures"]


def test_boot_store_includes_consistency_and_probe(tmp_path: Path):
    store = tmp_path / "agent-test"
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 3, "store": {"store_id": "agent-test"}})
    from casa.prisms.shared.store_persist import save_runtime_state

    save_field_to_db(store, state)
    save_runtime_state(store, state, force=True, thin=True, sync_ltm_on_save=False)
    (store / "ltm").mkdir()
    (store / "ltm" / "pack.manifest.json").write_text(
        '{"schema_version":1,"kind":"ltm_pack_manifest","lattices":{}}\n',
        encoding="utf-8",
    )

    boot = boot_store(store, prefer_field_state=True)
    assert "consistency" in boot
    assert boot["consistency"]["ok"] is True
    assert boot["router_probe"]["ok"] is True
