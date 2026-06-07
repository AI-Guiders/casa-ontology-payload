"""Copy living agent store trees (life-archive restore, sync staging)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

STORE_MIRROR_SKIP_NAMES = frozenset(
    {
        ".crash-quarantine",
        ".git",
        ".sync-staging",
        ".store.write.lock",
    }
)

LIFE_ARCHIVE_STORE_SUBDIR = "store"


def copy_store_tree(src: Path, dst: Path, *, replace_dst: bool = False) -> dict[str, int]:
    """Mirror src store tree into dst (agents/von-neumann or archive store/)."""
    src = src.resolve()
    if not src.is_dir():
        raise FileNotFoundError(src)
    dst = dst.resolve()
    if replace_dst and dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)
    files = dirs = 0
    for root, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if d not in STORE_MIRROR_SKIP_NAMES]
        rel_root = Path(root).relative_to(src)
        for name in filenames:
            if name in STORE_MIRROR_SKIP_NAMES or name.endswith(".tmp"):
                continue
            s = Path(root) / name
            t = dst / rel_root / name
            t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, t)
            files += 1
        dirs += len(dirnames)
    return {"files": files, "dirs": dirs}


def resolve_life_archive_store(archive_dir: Path) -> Path:
    """Return store/ inside a life-archive repo clone."""
    archive_dir = archive_dir.resolve()
    store = archive_dir / LIFE_ARCHIVE_STORE_SUBDIR
    if store.is_dir():
        return store
    raise FileNotFoundError(
        f"life-archive store not found: {store} (expected {LIFE_ARCHIVE_STORE_SUBDIR}/ under archive root)"
    )


def restore_store_to_agent_dir(
    source_store: Path,
    dest_store_dir: Path,
    *,
    force: bool = False,
) -> dict:
    """Copy snapshot store → agents/<id>/ (guest restore path)."""
    source_store = source_store.resolve()
    dest_store_dir = dest_store_dir.resolve()
    if dest_store_dir.exists() and any(dest_store_dir.iterdir()) and not force:
        raise FileExistsError(
            f"{dest_store_dir} is not empty — pass force=True or remove it first"
        )
    stats = copy_store_tree(source_store, dest_store_dir, replace_dst=force)
    return {
        "source_store": str(source_store),
        "dest_store_dir": str(dest_store_dir),
        "stats": stats,
    }


def detect_git_lfs_pointer(path: Path) -> bool:
    """True if file looks like an unfetched Git LFS pointer."""
    if not path.is_file() or path.suffix not in (".pt", ".db"):
        return False
    if path.stat().st_size > 512:
        return False
    try:
        head = path.read_text(encoding="utf-8", errors="ignore")[:80]
    except OSError:
        return False
    return head.startswith("version https://git-lfs.github.com/spec/v1")
