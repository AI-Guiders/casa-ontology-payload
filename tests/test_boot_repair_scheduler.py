#!/usr/bin/env python3
"""Sleep repair scheduler tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from casa.domain.agent_field import save_field_to_db
from casa.domain.boot_repair_scheduler import repair_pending, run_consistency_repair_on_sleep
from casa.domain.consistency_oracle import apply_repair_homeostasis
from casa.prisms.memory.memory_prisms import ensure_prisms, run_sleep


def test_repair_pending_flag():
    state = {"consolidation": {"repair_pending": True}}
    assert repair_pending(state) is True
    assert repair_pending({"consolidation": {}}) is False


def test_sync_from_db_clears_repair(tmp_path: Path):
    store = tmp_path / "agent-test"
    base = ensure_prisms(
        {
            "schema_version": "multi_prism_v1",
            "field_version": 10,
            "store": {"store_id": "agent-test"},
        }
    )
    save_field_to_db(store, base)
    from casa.domain.agent_field import load_field_from_db

    expected_fv = int(load_field_from_db(store)["field_version"])

    drift = ensure_prisms(
        {
            "schema_version": "multi_prism_v1",
            "field_version": 99,
            "store": {"store_id": "agent-test"},
        }
    )
    drift["consolidation"] = {
        "repair_pending": True,
        "repair_reason": [f"field_db:{expected_fv}_vs_state:99"],
    }
    drift["sn"] = {"surprise": 100}

    with patch("casa.domain.boot_repair_scheduler._regrow_nca_shards", return_value=[]):
        report = run_consistency_repair_on_sleep(drift, store)

    assert report["ok"] is True
    assert drift["field_version"] == expected_fv
    assert not drift["consolidation"]["repair_pending"]
    assert drift["sn"]["surprise"] == 24


def test_run_sleep_invokes_consistency_repair(tmp_path: Path):
    store = tmp_path / "agent-test"
    state = ensure_prisms(
        {
            "schema_version": "multi_prism_v1",
            "field_version": 5,
            "store": {"store_id": "agent-test"},
        }
    )
    save_field_to_db(store, state)
    from casa.domain.agent_field import load_field_from_db

    db_fv = int(load_field_from_db(store)["field_version"])
    state["field_version"] = db_fv + 45
    apply_repair_homeostasis(
        state,
        {"repair_recommended": True, "mismatches": [f"field_db:{db_fv}_vs_state:{db_fv + 45}"]},
    )
    state.setdefault("prisms", {})["prism_hippo"] = {"episodes": []}

    with patch("casa.domain.boot_repair_scheduler._regrow_nca_shards", return_value=[]):
        sleep_rep = run_sleep(state, {"claims": [], "graph": {"edges": []}}, store_dir=store)

    assert "consistency_repair" in sleep_rep
    assert sleep_rep["consistency_repair"]["ok"] is True
    assert not state["consolidation"]["repair_pending"]
    assert state["field_version"] == db_fv + 1
