"""Store write lock."""

from __future__ import annotations

from pathlib import Path

from casa.prisms.shared.store_lock import store_write_lock


def test_store_write_lock_reentrant_same_thread(tmp_path: Path) -> None:
    store = tmp_path / "agent"
    store.mkdir()
    with store_write_lock(store, holder="outer"):
        assert (store / ".store.write.lock").is_file()
        with store_write_lock(store, holder="inner"):
            assert (store / ".store.write.lock").is_file()
    assert not (store / ".store.write.lock").exists()
