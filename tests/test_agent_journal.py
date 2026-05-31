"""Agent journal — independent from ltm/ cartridges."""

from __future__ import annotations

from pathlib import Path

import pytest

from casa.prisms.memory.agent_journal import (
    append_journal_entry,
    delete_journal_entry,
    get_journal_entry,
    journal_stats,
    patch_journal_entry,
    read_journal_entries,
    safe_journal_domain,
)


def test_safe_domain_rejects_bad_names() -> None:
    assert safe_journal_domain("math") == "math"
    with pytest.raises(ValueError):
        safe_journal_domain("../escape")


def test_journal_roundtrip(tmp_path: Path) -> None:
    store = tmp_path / "sss-ru-general"
    store.mkdir()

    row = append_journal_entry(
        store,
        {
            "kind": "law",
            "text": "two sticks + two sticks = four sticks",
            "concepts": ["math.op.add"],
            "tokens": ["M:qty:2×entity:stick"],
        },
        domain="math",
    )
    assert row["id"].startswith("j-")

    rows = read_journal_entries(store, domain="math", concept="math.op.add")
    assert len(rows) == 1
    assert rows[0]["text"].startswith("two sticks")

    got = get_journal_entry(store, row["id"], domain="math")
    assert got is not None
    assert got["kind"] == "law"

    patched = patch_journal_entry(store, row["id"], {"text": "updated law"}, domain="math")
    assert patched is not None
    assert patched["text"] == "updated law"

    assert delete_journal_entry(store, row["id"], domain="math") is True
    assert read_journal_entries(store, domain="math") == []


def test_journal_stats(tmp_path: Path) -> None:
    store = tmp_path / "store"
    store.mkdir()
    append_journal_entry(store, {"text": "note a"}, domain="math")
    append_journal_entry(store, {"text": "note b"}, domain="general")
    stats = journal_stats(store)
    assert stats["entry_count"] == 2
    assert stats["domain_count"] == 2
