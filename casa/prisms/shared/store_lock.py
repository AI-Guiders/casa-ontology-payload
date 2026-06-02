#!/usr/bin/env python3
"""Cross-process exclusive lock for agent store writes (one writer per store_dir)."""

from __future__ import annotations

import contextlib
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

_LOCK_NAME = ".store.write.lock"
_DEFAULT_TIMEOUT_S = 600.0
_STALE_LOCK_S = 3600.0
_local = threading.local()


def _write_lock_depth() -> int:
    return int(getattr(_local, "store_write_depth", 0) or 0)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _lock_path(store_dir: Path) -> Path:
    return store_dir.resolve() / _LOCK_NAME


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _read_lock_meta(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _lock_is_stale(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        age_s = time.time() - path.stat().st_mtime
    except OSError:
        return True
    if age_s > _STALE_LOCK_S:
        return True
    meta = _read_lock_meta(path)
    pid = int(meta.get("pid") or 0)
    if pid and not _pid_alive(pid):
        return True
    return False


def _try_break_stale_lock(path: Path) -> None:
    if _lock_is_stale(path):
        path.unlink(missing_ok=True)


@contextlib.contextmanager
def store_write_lock(
    store_dir: Path,
    *,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
    poll_s: float = 0.25,
    holder: str | None = None,
) -> Iterator[Path]:
    """Exclusive store write lock — serializes field_state.json / ltm sync."""
    store_dir = store_dir.resolve()
    path = _lock_path(store_dir)
    if _write_lock_depth() > 0:
        _local.store_write_depth = _write_lock_depth() + 1
        try:
            yield path
        finally:
            _local.store_write_depth = _write_lock_depth() - 1
        return

    store_dir.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + max(0.1, timeout_s)
    fd: int | None = None
    meta = {
        "pid": os.getpid(),
        "since": _utc_now(),
        "holder": holder or "write",
    }

    while True:
        _try_break_stale_lock(path)
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, json.dumps(meta, ensure_ascii=False).encode("utf-8"))
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                owner = _read_lock_meta(path)
                raise TimeoutError(
                    f"store write lock busy: {path} holder={owner.get('holder')!r} pid={owner.get('pid')}"
                ) from None
            time.sleep(poll_s)

    _local.store_write_depth = 1
    try:
        yield path
    finally:
        _local.store_write_depth = 0
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        path.unlink(missing_ok=True)


@contextlib.contextmanager
def store_session_lock(
    store_dir: Path,
    *,
    holder: str,
    timeout_s: float = _DEFAULT_TIMEOUT_S,
) -> Iterator[Path]:
    """Long-lived lock for batch ingest / curriculum (blocks reactor persist)."""
    with store_write_lock(store_dir, timeout_s=timeout_s, holder=holder) as path:
        yield path
