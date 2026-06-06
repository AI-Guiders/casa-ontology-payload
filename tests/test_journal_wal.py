#!/usr/bin/env python3
"""Journal WAL replay and durable append."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from casa.domain.journal_wal import (
    append_entry_line,
    load_entries_safe,
    replay_journal_wal,
    wal_append_pending,
    wal_path,
)
from casa.domain.store_recovery import maybe_recover_store_on_wake
from casa.prisms.memory.agent_journal import append_journal_entry


def test_append_journal_entry_uses_wal_and_checkpoint(tmp_path: Path):
    store = tmp_path / "agent-test"
    row = append_journal_entry(
        store,
        {"kind": "note", "text": "hello wal"},
        domain="self",
        field_version=3,
    )
    assert row["id"].startswith("j-")
    assert (store / "journal" / "self" / "entries.jsonl").is_file()
    assert (store / "journal" / "checkpoint.json").is_file()
    assert wal_path(store).is_file() is False  # compacted after commit

    rows = load_entries_safe(store, "self")
    assert len(rows) == 1
    assert rows[0]["text"] == "hello wal"


def test_replay_pending_wal_after_crash_before_commit(tmp_path: Path):
    store = tmp_path / "agent-test"
    entry = {
        "id": "j-crash001",
        "ts": "2026-06-06T00:00:00Z",
        "kind": "note",
        "text": "orphan intent",
        "concepts": [],
        "tokens": [],
        "tags": [],
    }
    wal_append_pending(store, "self", entry, field_version=1)
    # crash before entries.jsonl write

    rep = replay_journal_wal(store)
    assert rep["replayed"] == ["j-crash001"]
    rows = load_entries_safe(store, "self")
    assert len(rows) == 1
    assert rows[0]["text"] == "orphan intent"


def test_load_entries_safe_trims_corrupt_tail(tmp_path: Path):
    store = tmp_path / "agent-test"
    path = store / "journal" / "self" / "entries.jsonl"
    path.parent.mkdir(parents=True)
    good = {"id": "j-1", "kind": "note", "text": "ok"}
    path.write_text(json.dumps(good) + "\n{\"broken\n", encoding="utf-8")

    rows = load_entries_safe(store, "self")
    assert len(rows) == 1
    assert "broken" not in path.read_text(encoding="utf-8")


def test_maybe_recover_includes_journal_wal_replay(tmp_path: Path):
    store = tmp_path / "agent-test"
    entry = {
        "id": "j-wake01",
        "ts": "2026-06-06T00:00:00Z",
        "kind": "note",
        "text": "wake replay",
        "concepts": [],
        "tokens": [],
        "tags": [],
    }
    wal_append_pending(store, "self", entry, field_version=0)
    rep = maybe_recover_store_on_wake(store)
    assert rep.get("journal_wal", {}).get("replayed") == ["j-wake01"]
