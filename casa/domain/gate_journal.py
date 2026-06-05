#!/usr/bin/env python3
"""Mastery gate attempts in agent_journal.db (mirror of knowledge_trace gates)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from casa.domain.agent_journal import migrate_legacy_session_arrays, open_journal


def append_gate_attempt(
    store_dir: Path,
    *,
    gate_id: str,
    passed: bool,
    tick: int,
    row: dict[str, Any],
    max_rows: int = 128,
) -> None:
    migrate_legacy_session_arrays(store_dir)
    with open_journal(store_dir) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS gate_attempt (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                at TEXT NOT NULL,
                gate_id TEXT NOT NULL,
                tick INTEGER,
                passed INTEGER NOT NULL,
                streak INTEGER,
                payload TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO gate_attempt (at, gate_id, tick, passed, streak, payload)
            VALUES (datetime('now'), ?, ?, ?, ?, ?)
            """,
            (
                str(gate_id or ""),
                int(tick or 0),
                1 if passed else 0,
                int(row.get("streak") or 0),
                json.dumps(row, ensure_ascii=False, separators=(",", ":")),
            ),
        )
        conn.execute(
            """
            DELETE FROM gate_attempt
            WHERE id NOT IN (SELECT id FROM gate_attempt ORDER BY id DESC LIMIT ?)
            """,
            (max(1, max_rows),),
        )
        conn.commit()
