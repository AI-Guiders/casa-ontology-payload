"""Agent journal — independent from ltm/ cartridges."""

from __future__ import annotations

from pathlib import Path

import pytest

from casa.prisms.memory.agent_journal import (
    DEFAULT_JOURNAL_DOMAIN,
    append_journal_entry,
    delete_journal_entry,
    find_journal_entry,
    get_journal_entry,
    journal_stats,
    notebook_tag,
    patch_journal_entry,
    read_journal_entries,
    safe_journal_domain,
    search_journal_entries,
)


def test_safe_domain_rejects_bad_names() -> None:
    assert safe_journal_domain("math") == "math"
    assert safe_journal_domain("self") == "self"
    with pytest.raises(ValueError):
        safe_journal_domain("../escape")


def test_journal_roundtrip(tmp_path: Path) -> None:
    store = tmp_path / "store"
    store.mkdir()

    row = append_journal_entry(
        store,
        {
            "kind": "law",
            "text": "two sticks + two sticks = four sticks",
            "concepts": ["math.op.add"],
            "tokens": ["M:qty:2×entity:stick"],
        },
    )
    assert row["id"].startswith("j-")

    rows = read_journal_entries(store, concept="math.op.add")
    assert len(rows) == 1
    assert rows[0]["text"].startswith("two sticks")

    got = get_journal_entry(store, row["id"])
    assert got is not None
    assert got["kind"] == "law"

    patched = patch_journal_entry(store, row["id"], {"text": "updated law"})
    assert patched is not None
    assert patched["text"] == "updated law"

    assert delete_journal_entry(store, row["id"]) is True
    assert read_journal_entries(store) == []


def test_journal_stats_and_notebook_search(tmp_path: Path) -> None:
    store = tmp_path / "store"
    store.mkdir()
    append_journal_entry(
        store,
        {
            "text": "note a",
            "tags": [notebook_tag("zettel-a")],
            "meta": {"notebook": "zettel-a"},
        },
        domain="self",
    )
    append_journal_entry(store, {"text": "note b"}, domain="math")
    stats = journal_stats(store)
    assert stats["entry_count"] == 2
    assert stats["domain_count"] == 2

    found = search_journal_entries(store, notebook="zettel-a")
    assert len(found) == 1
    assert found[0]["_domain"] == "self"

    cross = search_journal_entries(store, domain=None, query="note b")
    assert len(cross) == 1
    assert find_journal_entry(store, cross[0]["id"]) is not None


def test_default_domain_is_self(tmp_path: Path) -> None:
    store = tmp_path / "store"
    store.mkdir()
    row = append_journal_entry(store, {"text": "hello"})
    found = find_journal_entry(store, row["id"])
    assert found is not None
    assert found[1] == DEFAULT_JOURNAL_DOMAIN
