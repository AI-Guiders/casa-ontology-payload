#!/usr/bin/env python3
"""Subject journal storage backend — sqlite (default) or WitDB (ADR-0041)."""

from __future__ import annotations

import os
import shutil
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

JOURNAL_NAME_SQLITE = "agent_journal.db"
JOURNAL_NAME_WITDB = "agent_journal.witdb"

# Session meta and tests expect a stable symbol; reflects default backend filename.
JOURNAL_NAME = JOURNAL_NAME_SQLITE


@runtime_checkable
class JournalCursor(Protocol):
    @property
    def lastrowid(self) -> int: ...

    def fetchone(self) -> Any: ...

    def fetchall(self) -> list[Any]: ...


@runtime_checkable
class JournalConnection(Protocol):
    def execute(self, sql: str, params: Sequence[Any] | None = ...) -> JournalCursor: ...

    def executescript(self, sql: str) -> None: ...

    def commit(self) -> None: ...

    def close(self) -> None: ...


def journal_backend() -> str:
    raw = os.environ.get("CASA_JOURNAL_BACKEND", "sqlite").strip().lower()
    if raw in ("witdb", "native", "auto"):
        return "witdb"
    return "sqlite"


def journal_filename() -> str:
    return JOURNAL_NAME_WITDB if journal_backend() == "witdb" else JOURNAL_NAME_SQLITE


def journal_path(store_dir: Path) -> Path:
    return store_dir.resolve() / journal_filename()


def legacy_sqlite_journal_path(store_dir: Path) -> Path:
    return store_dir.resolve() / JOURNAL_NAME_SQLITE


def _open_sqlite(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _open_witdb(path: Path) -> JournalConnection:
    try:
        import pywitdb.sql as wsql
        from pywitdb._bridge.client import bridge_available
        from pywitdb.exceptions import BridgeNotAvailableError, WitDbStoreError
    except ImportError as exc:
        raise RuntimeError(
            "CASA_JOURNAL_BACKEND=witdb requires pywitdb; install from Financial/software/open/pywitdb"
        ) from exc

    backend = "auto"
    if backend == "auto" and not bridge_available():
        try:
            from pywitdb._native.client import native_available
        except ImportError:
            native_available = lambda: False  # noqa: E731
        if not native_available():
            raise BridgeNotAvailableError(
                "witdb journal: neither native nor bridge available; "
                "build WitDbBridge or enable native SQL (pywitdb ADR-0004 §4–5)"
            )

    conn = wsql.connect(str(path), backend=backend, create=True)
    return conn  # type: ignore[return-value]


@contextmanager
def open_journal_conn(store_dir: Path) -> Iterator[JournalConnection]:
    store_dir = store_dir.resolve()
    store_dir.mkdir(parents=True, exist_ok=True)
    path = journal_path(store_dir)
    backend = journal_backend()

    if backend == "witdb":
        legacy = legacy_sqlite_journal_path(store_dir)
        if not path.is_file() and legacy.is_file():
            migrate_sqlite_journal_to_witdb(store_dir)
        conn = _open_witdb(path)
    else:
        conn = _open_sqlite(path)

    try:
        yield conn
    finally:
        conn.close()


def migrate_sqlite_journal_to_witdb(store_dir: Path, *, keep_backup: bool = True) -> dict[str, int]:
    """Copy rows from agent_journal.db into agent_journal.witdb (one-shot)."""
    if journal_backend() != "witdb":
        raise RuntimeError("migrate_sqlite_journal_to_witdb requires CASA_JOURNAL_BACKEND=witdb")

    store_dir = store_dir.resolve()
    src = legacy_sqlite_journal_path(store_dir)
    dst = journal_path(store_dir)
    if not src.is_file():
        return {}
    if dst.is_file():
        return {}

    from casa.domain.agent_journal import JOURNAL_CREATE_SQL

    counts: dict[str, int] = {}
    tables = ("skill_trace", "tick_log", "experience", "retrospective")

    with _open_sqlite(src) as src_conn, _open_witdb(dst) as dst_conn:
        dst_conn.executescript(JOURNAL_CREATE_SQL)
        for table in tables:
            rows = src_conn.execute(f"SELECT * FROM {table} ORDER BY id ASC").fetchall()
            if not rows:
                continue
            cols = rows[0].keys()
            placeholders = ", ".join("?" for _ in cols)
            col_list = ", ".join(cols)
            for row in rows:
                dst_conn.execute(
                    f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",
                    tuple(row[c] for c in cols),
                )
            counts[table] = len(rows)
        dst_conn.commit()

    if keep_backup:
        bak = src.with_suffix(src.suffix + ".bak")
        if not bak.is_file():
            shutil.move(str(src), str(bak))

    return counts
