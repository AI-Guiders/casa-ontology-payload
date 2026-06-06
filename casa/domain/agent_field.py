#!/usr/bin/env python3
"""Agent field store — SQLite routes + compressed body (ADR-0039)."""

from __future__ import annotations

import copy
import gzip
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from casa.domain.routing import Route, Router
from casa.prisms.control.fpn_state import read_session_meta, write_session_meta
from casa.prisms.memory.memory_prisms import ensure_prisms

FIELD_DB_NAME = "agent_field.db"
_SCHEMA_VERSION = 1

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value_text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_kind TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    match_json TEXT NOT NULL,
    target_prism TEXT,
    lattice_hint TEXT,
    target_skill TEXT,
    target_goal TEXT,
    target_plan TEXT,
    steps_json TEXT,
    provenance_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_routes_kind ON routes(route_kind);
CREATE TABLE IF NOT EXISTS chunks (
    name TEXT PRIMARY KEY,
    codec TEXT NOT NULL,
    blob BLOB NOT NULL
);
"""


def field_db_path(store_dir: Path) -> Path:
    return store_dir.resolve() / FIELD_DB_NAME


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def _compress_json(obj: Any) -> bytes:
    raw = _json_dumps(obj).encode("utf-8")
    return gzip.compress(raw, compresslevel=6)


def _decompress_json(blob: bytes) -> Any:
    raw = gzip.decompress(blob)
    return json.loads(raw.decode("utf-8"))


@contextmanager
def open_field_db(store_dir: Path) -> Iterator[sqlite3.Connection]:
    path = field_db_path(store_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(_CREATE_SQL)
        conn.commit()
        yield conn
    finally:
        conn.close()


def _clear_routes_in_body(state: dict[str, Any]) -> dict[str, Any]:
    body = copy.deepcopy(state)
    prisms = body.get("prisms")
    if isinstance(prisms, dict):
        for key in ("prism_router", "prism_control_router"):
            block = prisms.get(key)
            if isinstance(block, dict):
                block["routes"] = []
    router = body.get("router")
    if isinstance(router, dict):
        router["routes"] = []
    return body


def _extract_routes(state: dict[str, Any]) -> list[Route]:
    try:
        return Router.bind(state).routes()
    except Exception:
        return []


def _inject_routes(state: dict[str, Any], routes: list[Route]) -> dict[str, Any]:
    runtime = ensure_prisms(state)
    Router.bind(runtime).set_routes(routes)
    return runtime


def save_field_to_db(store_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    """Persist field: routes table + gzip body chunk."""
    store_dir = store_dir.resolve()
    routes = _extract_routes(state)
    body = _state_body_without_routes(state)
    meta_keys = {
        "schema_version": str(state.get("schema_version") or ""),
        "field_version": str(int(state.get("field_version") or 0)),
        "updated_at": str(state.get("updated_at") or datetime.now(timezone.utc).isoformat()),
    }

    with open_field_db(store_dir) as conn:
        conn.execute("DELETE FROM routes")
        conn.execute("DELETE FROM meta")
        for key, val in meta_keys.items():
            conn.execute("INSERT INTO meta(key, value_text) VALUES (?, ?)", (key, val))
        for route in routes:
            row = route.to_row()
            conn.execute(
                """
                INSERT INTO routes (
                    route_kind, priority, match_json, target_prism, lattice_hint,
                    target_skill, target_goal, target_plan, steps_json, provenance_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.get("route_kind") or "knowledge",
                    int(row.get("priority") or 0),
                    _json_dumps(row.get("match") or {}),
                    row.get("target_prism") or "",
                    row.get("lattice_hint") or "",
                    row.get("target_skill") or "",
                    row.get("target_goal") or "",
                    row.get("target_plan") or "",
                    _json_dumps(row.get("steps") or []),
                    _json_dumps(row.get("provenance") or {}),
                ),
            )
        conn.execute(
            """
            INSERT INTO chunks(name, codec, blob) VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET codec=excluded.codec, blob=excluded.blob
            """,
            ("field_body", "gzip+json", _compress_json(body)),
        )
        conn.commit()

    meta = read_session_meta(store_dir)
    meta["field_db"] = FIELD_DB_NAME
    meta["field_db_at"] = meta_keys["updated_at"]
    write_session_meta(store_dir, meta)
    return {"routes": len(routes), "field_version": meta_keys["field_version"]}


def _state_body_without_routes(state: dict[str, Any]) -> dict[str, Any]:
    return _clear_routes_in_body(state)


def load_field_from_db(store_dir: Path) -> dict[str, Any] | None:
    """Load field from agent_field.db; None if missing."""
    if not field_db_path(store_dir).is_file():
        return None
    with open_field_db(store_dir) as conn:
        chunk = conn.execute("SELECT blob FROM chunks WHERE name = ?", ("field_body",)).fetchone()
        if chunk is None:
            return None
        body = _decompress_json(chunk["blob"])
        rows = conn.execute("SELECT * FROM routes ORDER BY priority DESC, id ASC").fetchall()
        meta_rows = conn.execute("SELECT key, value_text FROM meta").fetchall()

    routes: list[Route] = []
    for row in rows:
        routes.append(
            Route.from_row(
                {
                    "route_kind": row["route_kind"],
                    "priority": row["priority"],
                    "match": json.loads(row["match_json"]),
                    "target_prism": row["target_prism"],
                    "lattice_hint": row["lattice_hint"] or None,
                    "target_skill": row["target_skill"],
                    "target_goal": row["target_goal"],
                    "target_plan": row["target_plan"],
                    "steps": json.loads(row["steps_json"] or "[]"),
                    "provenance": json.loads(row["provenance_json"] or "{}"),
                }
            )
        )

    state = _inject_routes(body if isinstance(body, dict) else {}, routes)
    for row in meta_rows:
        key = row["key"]
        if key == "field_version":
            state["field_version"] = int(row["value_text"] or 0)
        elif key == "schema_version" and row["value_text"]:
            state["schema_version"] = row["value_text"]
        elif key == "updated_at":
            state["updated_at"] = row["value_text"]
    return state


def field_db_stats(store_dir: Path) -> dict[str, Any]:
    if not field_db_path(store_dir).is_file():
        return {"ok": False}
    with open_field_db(store_dir) as conn:
        routes = conn.execute("SELECT COUNT(*) AS c FROM routes").fetchone()["c"]
        chunk = conn.execute("SELECT LENGTH(blob) AS n FROM chunks WHERE name='field_body'").fetchone()
        meta_rows = conn.execute("SELECT key, value_text FROM meta").fetchall()
    meta = {row["key"]: row["value_text"] for row in meta_rows}
    fv_raw = meta.get("field_version")
    out: dict[str, Any] = {
        "ok": True,
        "path": str(field_db_path(store_dir)),
        "routes": int(routes),
        "body_bytes": int(chunk["n"] if chunk else 0),
    }
    if fv_raw is not None:
        try:
            out["field_version"] = int(fv_raw)
        except (TypeError, ValueError):
            pass
    return out


def import_field_from_json(store_dir: Path, json_path: Path) -> dict[str, Any]:
    """One-shot migrate field_state.json → agent_field.db."""
    state = json.loads(json_path.read_text(encoding="utf-8"))
    return save_field_to_db(store_dir, ensure_prisms(state))
