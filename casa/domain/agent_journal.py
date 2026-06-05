#!/usr/bin/env python3
"""Subject journal — SQLite append log (ADR-0038)."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from casa.prisms.control.fpn_state import SESSION_NAME, session_path, write_session_meta

JOURNAL_NAME = "agent_journal.db"
_SCHEMA_VERSION = 1

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS skill_trace (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    tick INTEGER,
    goal_id TEXT,
    skill TEXT,
    plan_step INTEGER,
    outcome TEXT,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_skill_trace_goal ON skill_trace(goal_id);
CREATE INDEX IF NOT EXISTS idx_skill_trace_skill ON skill_trace(skill);
CREATE INDEX IF NOT EXISTS idx_skill_trace_outcome ON skill_trace(outcome);

CREATE TABLE IF NOT EXISTS tick_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    tick INTEGER,
    query TEXT,
    goal_id TEXT,
    step_capability TEXT,
    srl TEXT,
    outcome TEXT,
    check_passed INTEGER,
    surprise INTEGER,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tick_log_tick ON tick_log(tick);

CREATE TABLE IF NOT EXISTS experience (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    tick INTEGER,
    name TEXT,
    title TEXT,
    outcome TEXT,
    payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS retrospective (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    window INTEGER,
    entries_analyzed INTEGER,
    payload TEXT NOT NULL
);
"""


def journal_path(store_dir: Path) -> Path:
    return store_dir.resolve() / JOURNAL_NAME


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _json_loads(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        val = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return val if isinstance(val, dict) else {}


@contextmanager
def open_journal(store_dir: Path) -> Iterator[sqlite3.Connection]:
    path = journal_path(store_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(_CREATE_SQL)
        conn.commit()
        yield conn
    finally:
        conn.close()


def _prune(conn: sqlite3.Connection, table: str, *, max_rows: int) -> None:
    conn.execute(
        f"""
        DELETE FROM {table}
        WHERE id NOT IN (
            SELECT id FROM {table} ORDER BY id DESC LIMIT ?
        )
        """,
        (max(1, max_rows),),
    )


_inflight_migrate: set[str] = set()


def migrate_legacy_session_arrays(store_dir: Path) -> dict[str, int]:
    """One-time import from agent_session.json arrays into SQLite."""
    key = str(store_dir.resolve())
    if key in _inflight_migrate:
        return {}
    path = session_path(store_dir)
    if not path.is_file():
        return {}
    try:
        session = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(session, dict) or session.get("journal_migrated"):
        return {}

    imported: dict[str, int] = {}
    _inflight_migrate.add(key)
    try:
        with open_journal(store_dir) as conn:
            for row in session.get("skill_trace") or []:
                if isinstance(row, dict):
                    insert_skill_trace(conn, row, prune_max=0)
                    imported["skill_trace"] = imported.get("skill_trace", 0) + 1
            for row in session.get("tick_log") or []:
                if isinstance(row, dict):
                    insert_tick_log(conn, row, prune_max=0)
                    imported["tick_log"] = imported.get("tick_log", 0) + 1
            for row in session.get("experience_ledger") or []:
                if isinstance(row, dict):
                    insert_experience(conn, row, prune_max=0)
                    imported["experience"] = imported.get("experience", 0) + 1
            for row in session.get("retrospective") or []:
                if isinstance(row, dict):
                    insert_retrospective(conn, row)
                    imported["retrospective"] = imported.get("retrospective", 0) + 1
            tick_count = int(conn.execute("SELECT COUNT(*) AS c FROM tick_log").fetchone()["c"])
            conn.commit()

        if imported or session.get("skill_trace") or session.get("tick_log"):
            meta = {
                "schema_version": 2,
                "journal": JOURNAL_NAME,
                "journal_migrated": True,
                "wm": session.get("wm") if isinstance(session.get("wm"), dict) else {},
                "macro_ticks": int(session.get("macro_ticks") or tick_count),
                "updated_at": session.get("updated_at") or _utc_now(),
            }
            write_session_meta(store_dir, meta)
    finally:
        _inflight_migrate.discard(key)
    return imported


def insert_skill_trace(
    conn: sqlite3.Connection,
    entry: dict[str, Any],
    *,
    prune_max: int = 96,
) -> int:
    sit = entry.get("situation") if isinstance(entry.get("situation"), dict) else {}
    cur = conn.execute(
        """
        INSERT INTO skill_trace (at, tick, goal_id, skill, plan_step, outcome, payload)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(entry.get("at") or _utc_now()),
            entry.get("tick"),
            str(sit.get("goal_id") or ""),
            str(entry.get("skill") or ""),
            int(entry.get("plan_step") or 0),
            str(entry.get("outcome") or ""),
            _json_dumps(entry),
        ),
    )
    if prune_max:
        _prune(conn, "skill_trace", max_rows=prune_max)
    return int(cur.lastrowid or 0)


def insert_tick_log(
    conn: sqlite3.Connection,
    entry: dict[str, Any],
    *,
    prune_max: int = 64,
) -> int:
    executor = entry.get("executor") if isinstance(entry.get("executor"), dict) else {}
    check = entry.get("check") if isinstance(entry.get("check"), dict) else {}
    cur = conn.execute(
        """
        INSERT INTO tick_log (at, tick, query, goal_id, step_capability, srl, outcome, check_passed, surprise, payload)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(entry.get("at") or _utc_now()),
            entry.get("tick"),
            str(entry.get("query") or ""),
            str(executor.get("goal_id") or ""),
            str(executor.get("step_capability") or ""),
            str(entry.get("srl") or ""),
            str(entry.get("outcome") or ""),
            1 if check.get("check_passed") else 0,
            1 if check.get("surprise") else 0,
            _json_dumps(entry),
        ),
    )
    if prune_max:
        _prune(conn, "tick_log", max_rows=prune_max)
    return int(cur.lastrowid or 0)


def insert_experience(
    conn: sqlite3.Connection,
    entry: dict[str, Any],
    *,
    prune_max: int = 48,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO experience (at, tick, name, title, outcome, payload)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            str(entry.get("at") or _utc_now()),
            entry.get("tick"),
            str(entry.get("name") or ""),
            str(entry.get("title") or ""),
            str(entry.get("outcome") or ""),
            _json_dumps(entry),
        ),
    )
    if prune_max:
        _prune(conn, "experience", max_rows=prune_max)
    return int(cur.lastrowid or 0)


def insert_retrospective(conn: sqlite3.Connection, retro: dict[str, Any]) -> int:
    cur = conn.execute(
        """
        INSERT INTO retrospective (at, window, entries_analyzed, payload)
        VALUES (?, ?, ?, ?)
        """,
        (
            str(retro.get("at") or _utc_now()),
            int(retro.get("window") or 0),
            int(retro.get("entries_analyzed") or 0),
            _json_dumps(retro),
        ),
    )
    _prune(conn, "retrospective", max_rows=24)
    return int(cur.lastrowid or 0)


def append_skill_trace(store_dir: Path, entry: dict[str, Any], *, max_rows: int = 96) -> None:
    migrate_legacy_session_arrays(store_dir)
    with open_journal(store_dir) as conn:
        insert_skill_trace(conn, entry, prune_max=max_rows)
        conn.commit()


def append_tick_log_entry(store_dir: Path, entry: dict[str, Any], *, max_rows: int = 64) -> None:
    migrate_legacy_session_arrays(store_dir)
    with open_journal(store_dir) as conn:
        insert_tick_log(conn, entry, prune_max=max_rows)
        conn.commit()


def append_experience_entry(store_dir: Path, entry: dict[str, Any], *, max_rows: int = 48) -> None:
    migrate_legacy_session_arrays(store_dir)
    with open_journal(store_dir) as conn:
        insert_experience(conn, entry, prune_max=max_rows)
        conn.commit()


def append_retrospective_entry(store_dir: Path, retro: dict[str, Any]) -> None:
    migrate_legacy_session_arrays(store_dir)
    with open_journal(store_dir) as conn:
        insert_retrospective(conn, retro)
        conn.commit()


def _rows_to_payload(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        payload = _json_loads(row["payload"])
        if payload:
            out.append(payload)
    return out


def query_skill_trace(
    store_dir: Path,
    *,
    goal_id: str = "",
    skill: str = "",
    outcome: str = "",
    limit: int = 32,
) -> list[dict[str, Any]]:
    migrate_legacy_session_arrays(store_dir)
    clauses = []
    params: list[Any] = []
    if goal_id.strip():
        clauses.append("goal_id LIKE ?")
        params.append(f"%{goal_id.strip()}%")
    if skill.strip():
        clauses.append("skill LIKE ?")
        params.append(f"%{skill.strip()}%")
    if outcome.strip():
        clauses.append("outcome = ?")
        params.append(outcome.strip())
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(max(1, limit))
    with open_journal(store_dir) as conn:
        rows = conn.execute(
            f"SELECT payload FROM skill_trace {where} ORDER BY id DESC LIMIT ?",
            params,
        ).fetchall()
    return _rows_to_payload(rows)


def recent_skill_trace(store_dir: Path, *, limit: int = 16) -> list[dict[str, Any]]:
    migrate_legacy_session_arrays(store_dir)
    with open_journal(store_dir) as conn:
        rows = conn.execute(
            "SELECT payload FROM skill_trace ORDER BY id DESC LIMIT ?",
            (max(1, limit),),
        ).fetchall()
    return list(reversed(_rows_to_payload(rows)))


def last_skill_trace(store_dir: Path) -> dict[str, Any]:
    rows = query_skill_trace(store_dir, limit=1)
    return rows[0] if rows else {}


def skill_trace_aggregate(store_dir: Path) -> dict[str, Any]:
    migrate_legacy_session_arrays(store_dir)
    with open_journal(store_dir) as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM skill_trace").fetchone()["c"]
        rows = conn.execute(
            "SELECT skill, outcome, COUNT(*) AS c FROM skill_trace GROUP BY skill, outcome"
        ).fetchall()
        goals = conn.execute(
            "SELECT goal_id, COUNT(*) AS c FROM skill_trace GROUP BY goal_id"
        ).fetchall()
    by_skill: dict[str, dict[str, int]] = {}
    by_outcome: dict[str, int] = {}
    for row in rows:
        sk = str(row["skill"] or "unknown")
        oc = str(row["outcome"] or "unknown")
        by_skill.setdefault(sk, {})[oc] = int(row["c"])
        by_outcome[oc] = by_outcome.get(oc, 0) + int(row["c"])
    by_goal = {str(r["goal_id"] or "unknown"): int(r["c"]) for r in goals}
    return {
        "entries": int(total),
        "by_skill": by_skill,
        "by_goal": by_goal,
        "by_outcome": by_outcome,
    }


def count_tick_log(store_dir: Path) -> int:
    migrate_legacy_session_arrays(store_dir)
    if not journal_path(store_dir).is_file():
        return 0
    with open_journal(store_dir) as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM tick_log").fetchone()
    return int(row["c"] if row else 0)


def recent_experience(store_dir: Path, *, limit: int = 8) -> list[dict[str, Any]]:
    migrate_legacy_session_arrays(store_dir)
    with open_journal(store_dir) as conn:
        rows = conn.execute(
            "SELECT payload FROM experience ORDER BY id DESC LIMIT ?",
            (max(1, limit),),
        ).fetchall()
    return list(reversed(_rows_to_payload(rows)))


def experience_outcome_counts(store_dir: Path) -> dict[str, int]:
    migrate_legacy_session_arrays(store_dir)
    with open_journal(store_dir) as conn:
        rows = conn.execute(
            "SELECT outcome, COUNT(*) AS c FROM experience GROUP BY outcome"
        ).fetchall()
    return {str(r["outcome"] or "unknown"): int(r["c"]) for r in rows}


def count_skill_trace(store_dir: Path) -> int:
    """Total skill_trace rows in journal."""
    return int(skill_trace_aggregate(store_dir).get("entries") or 0)


def last_retrospective(store_dir: Path) -> dict[str, Any]:
    migrate_legacy_session_arrays(store_dir)
    with open_journal(store_dir) as conn:
        row = conn.execute(
            "SELECT payload FROM retrospective ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return _json_loads(row["payload"]) if row else {}


def count_retrospectives(store_dir: Path) -> int:
    migrate_legacy_session_arrays(store_dir)
    if not journal_path(store_dir).is_file():
        return 0
    with open_journal(store_dir) as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM retrospective").fetchone()
    return int(row["c"] if row else 0)


def bump_macro_ticks(store_dir: Path, *, at: str | None = None) -> int:
    """Increment macro_ticks in slim session after tick_log append."""
    path = session_path(store_dir)
    meta: dict[str, Any] = {"schema_version": 2, "journal": JOURNAL_NAME}
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                meta = dict(raw)
        except (OSError, json.JSONDecodeError):
            pass
    ticks = int(meta.get("macro_ticks") or 0) + 1
    meta["schema_version"] = 2
    meta["journal"] = JOURNAL_NAME
    meta["macro_ticks"] = ticks
    meta["updated_at"] = at or _utc_now()
    write_session_meta(store_dir, meta)
    return ticks
