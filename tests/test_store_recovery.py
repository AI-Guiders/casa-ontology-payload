#!/usr/bin/env python3
"""Store checkpoint recovery after crash-zeroed JSON."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from casa.domain.agent_field import save_field_to_db
from casa.domain.store_recovery import (
    is_unreadable_json_file,
    is_zeroed_file,
    load_ltm_pack_manifest,
    maybe_recover_store_on_wake,
    recover_store_checkpoints,
)
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.shared.store_boot import boot_store


def _zeroed_file(path: Path, size: int = 128) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00" * size)


def test_is_zeroed_and_unreadable_json(tmp_path: Path):
    good = tmp_path / "ok.json"
    good.write_text('{"a":1}\n', encoding="utf-8")
    bad = tmp_path / "bad.json"
    _zeroed_file(bad, 64)

    assert not is_zeroed_file(good)
    assert is_zeroed_file(bad)
    assert not is_unreadable_json_file(good)
    assert is_unreadable_json_file(bad)


def test_recover_quarantines_and_boots_from_field_db(tmp_path: Path):
    store = tmp_path / "agent-test"
    ltm = store / "ltm"
    ltm.mkdir(parents=True)
    (ltm / "meta").mkdir()

    state = ensure_prisms(
        {
            "schema_version": "multi_prism_v1",
            "field_version": 7,
            "store": {"store_id": "agent-test"},
        }
    )
    save_field_to_db(store, state)

    _zeroed_file(ltm / "pack.manifest.json", 256)
    _zeroed_file(store / "field_state.json", 512)

    report = recover_store_checkpoints(store, persist_thin=True)
    assert report["recovered"] is True
    assert "pack.manifest.json" in report["quarantined"]
    assert (ltm / "pack.manifest.json").is_file()
    assert json.loads((ltm / "pack.manifest.json").read_text(encoding="utf-8"))["kind"] == "ltm_pack_manifest"
    assert (store / ".crash-quarantine").is_dir()

    boot = boot_store(store, prefer_field_state=True)
    assert boot["source"] == "field_state"
    assert boot["state"]["store"]["store_id"] == "agent-test"
    assert boot["state"].get("field_version", 0) >= 7


def test_maybe_recover_on_wake_idempotent(tmp_path: Path):
    store = tmp_path / "agent-test2"
    ltm = store / "ltm"
    ltm.mkdir(parents=True)
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 1, "store": {"store_id": "agent-test2"}})
    save_field_to_db(store, state)
    _zeroed_file(ltm / "pack.manifest.json", 64)

    r1 = maybe_recover_store_on_wake(store)
    r2 = maybe_recover_store_on_wake(store)
    assert r1["recovered"] is True
    assert r2["recovered"] is False


def test_load_ltm_pack_manifest_writes_stub_when_missing(tmp_path: Path):
    ltm = tmp_path / "ltm"
    ltm.mkdir()
    doc = load_ltm_pack_manifest(ltm)
    assert doc["lattices"] == {}
    assert (ltm / "pack.manifest.json").is_file()
