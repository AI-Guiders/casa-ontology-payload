from __future__ import annotations

import tempfile
from pathlib import Path

from casa.prisms.shared.store_mirror import copy_store_tree, resolve_life_archive_store


def test_copy_store_tree_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "src"
        dst = Path(tmp) / "dst"
        (src / "ltm").mkdir(parents=True)
        (src / "ltm" / "pack.manifest.json").write_text("{}", encoding="utf-8")
        (src / "nca" / "shard-a").mkdir(parents=True)
        (src / "nca" / "shard-a" / "model.pt").write_bytes(b"\x00" * 64)

        stats = copy_store_tree(src, dst)
        assert stats["files"] == 2
        assert (dst / "ltm" / "pack.manifest.json").is_file()
        assert (dst / "nca" / "shard-a" / "model.pt").read_bytes() == b"\x00" * 64


def test_resolve_life_archive_store():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "store" / "journal").mkdir(parents=True)
        assert resolve_life_archive_store(root) == root / "store"
