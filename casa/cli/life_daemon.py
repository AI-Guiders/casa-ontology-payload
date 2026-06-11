#!/usr/bin/env python3
"""Ensure unified life reactor is running for partner chat."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

from casa.body.text_tract import reactor_alive
from casa.prisms.shared.store_layout import default_agent_store


def default_teacher_inbox(store_dir: Path) -> Path:
    """Teacher-only lesson inbox (not partner chat)."""
    return store_dir.resolve() / "teacher_inbox"


def reactor_runner_script() -> Path:
    return REPO_ROOT / "tools" / "agent_inbox_runner.py"


def spawn_unified_reactor(
    store_dir: Path,
    *,
    inbox_dir: Path | None = None,
    poll_ms: int = 500,
    detached_window: bool = True,
) -> subprocess.Popen[bytes] | subprocess.Popen[str]:
    inbox = (inbox_dir or default_teacher_inbox(store_dir)).resolve()
    inbox.mkdir(parents=True, exist_ok=True)
    script = reactor_runner_script()
    store = store_dir.resolve()
    cmd = [
        sys.executable,
        str(script),
        "--store-dir",
        str(store),
        "--inbox-dir",
        str(inbox),
        "--poll-ms",
        str(poll_ms),
    ]
    if sys.platform == "win32" and detached_window:
        # Minimized console «CASA life» — visible in taskbar, not headless.
        # (Broken `start ... "" python` caused `'m' is not recognized`.)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore[attr-defined]
        startupinfo.wShowWindow = 7  # SW_SHOWMINNOACTIVE
        return subprocess.Popen(
            cmd,
            cwd=str(REPO_ROOT),
            creationflags=subprocess.CREATE_NEW_CONSOLE,  # type: ignore[attr-defined]
            startupinfo=startupinfo,
        )

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    return subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        creationflags=creationflags,
    )


def ensure_life_reactor(
    store_dir: Path | None = None,
    *,
    inbox_dir: Path | None = None,
    spawn: bool = True,
    boot_timeout_s: float = 120.0,
) -> bool:
    """Return True when pulse shows a live reactor; optionally spawn one."""
    store = (store_dir or default_agent_store()).resolve()
    if reactor_alive(store):
        return True
    if not spawn:
        return False
    proc = spawn_unified_reactor(store, inbox_dir=inbox_dir)
    import time

    deadline = time.monotonic() + max(15.0, boot_timeout_s)
    last_msg = 0.0
    while time.monotonic() < deadline:
        if reactor_alive(store):
            return True
        if proc.poll() is not None:
            print(
                "life reactor завершился при старте — смотри окно CASA life",
                file=sys.stderr,
                flush=True,
            )
            return False
        now = time.monotonic()
        if now - last_msg >= 2.0:
            print("  · жду life reactor (загрузка store)…", file=sys.stderr, flush=True)
            last_msg = now
        time.sleep(0.25)
    print(
        f"life reactor не ответил за {boot_timeout_s:.0f} с — store может грузиться дольше",
        file=sys.stderr,
        flush=True,
    )
    return False
