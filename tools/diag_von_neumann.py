#!/usr/bin/env python3
"""Post-crash diagnostics for agents/von-neumann store."""

from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa._paths import ensure_import_paths

ensure_import_paths()

STORE = _REPO / "agents" / "von-neumann"


def _file_health(path: Path) -> dict:
    if not path.exists():
        return {"path": str(path), "exists": False}
    raw = path.read_bytes()
    nulls = raw.count(0)
    text_ok = False
    err = None
    summary: dict = {}
    if path.suffix == ".json" and nulls < len(raw):
        try:
            doc = json.loads(raw.decode("utf-8"))
            text_ok = True
            summary = {
                k: doc.get(k)
                for k in ("schema_version", "field_version", "macro_ticks", "store_id")
                if k in doc or (k == "store_id" and isinstance(doc.get("store"), dict))
            }
            if "store" in doc and isinstance(doc["store"], dict):
                summary["store_id"] = doc["store"].get("store_id")
        except Exception as exc:
            err = str(exc)
    return {
        "path": str(path.name),
        "bytes": len(raw),
        "null_pct": round(100 * nulls / max(1, len(raw)), 1),
        "json_ok": text_ok,
        "json_err": err,
        "summary": summary,
    }


def _sqlite_health(path: Path) -> dict:
    con = sqlite3.connect(path)
    try:
        integrity = con.execute("pragma integrity_check").fetchone()[0]
        tables = [r[0] for r in con.execute("select name from sqlite_master where type='table' order by 1")]
        counts = {}
        for t in tables[:12]:
            try:
                counts[t] = con.execute(f"select count(*) from [{t}]").fetchone()[0]
            except sqlite3.Error as exc:
                counts[t] = f"err:{exc}"
        return {"path": path.name, "integrity": integrity, "tables": len(tables), "counts": counts}
    finally:
        con.close()


def _boot_probe() -> dict:
    from casa.cli.ingest_state import resolve_ingest_state
    from casa.prisms.memory.agent_life import load_agent_session
    from casa.prisms.memory.memory_prisms import ensure_prisms

    out: dict = {}
    t0 = time.perf_counter()
    try:
        session = load_agent_session(STORE)
        out["session_load"] = "ok"
        out["session_keys"] = list(session.keys())[:8]
        out["macro_ticks"] = session.get("macro_ticks")
    except Exception as exc:
        out["session_load"] = f"fail:{exc}"
    try:
        state = resolve_ingest_state(STORE, None)
        state = ensure_prisms(state)
        out["state_load"] = "ok"
        out["field_version"] = state.get("field_version")
        out["store_id"] = (state.get("store") or {}).get("store_id")
        vis = ((state.get("prisms") or {}).get("visual") or {}).get("cells")
        out["visual_cells"] = len(vis) if isinstance(vis, dict) else None
    except Exception as exc:
        out["state_load"] = f"fail:{exc}"
    out["load_sec"] = round(time.perf_counter() - t0, 2)
    return out


def _wake_once() -> dict:
    from casa.prisms.memory.agent_life import agent_wake

    t0 = time.perf_counter()
    try:
        rep = agent_wake(STORE, stop_after=1, persist=False)
        return {
            "ok": True,
            "sec": round(time.perf_counter() - t0, 2),
            "macro_ticks": rep.get("macro_ticks"),
            "quanta": rep.get("quanta_this_wake"),
        }
    except Exception as exc:
        return {"ok": False, "sec": round(time.perf_counter() - t0, 2), "error": str(exc)}


def _recovery_meta() -> dict:
    from casa.domain.store_recovery import recovery_warnings_from_session
    from casa.prisms.control.fpn_state import read_session_meta

    meta = read_session_meta(STORE)
    return {
        "last_recovery_at": meta.get("last_store_recovery_at"),
        "last_recovery_ok": meta.get("last_store_recovery_ok"),
        "quarantined": meta.get("last_store_recovery_quarantined"),
        "warnings": recovery_warnings_from_session(STORE),
        "quarantine_dir_exists": (STORE / ".crash-quarantine").is_dir(),
    }


def main() -> None:
    report = {
        "store": str(STORE),
        "recovery": _recovery_meta(),
        "files": [
            _file_health(STORE / name)
            for name in (
                "field_state.json",
                "field_state.before_sleep_e2e.json",
                "field_state.legacy.json",
                "agent_session.json",
                "memory_manifest.json",
            )
        ],
        "sqlite": [
            _sqlite_health(STORE / name)
            for name in ("agent_field.db", "agent_journal.db")
        ],
    }
    report["boot"] = _boot_probe()
    report["wake_once"] = _wake_once()
    trace_path = STORE / "nervous" / "impulse_trace.jsonl"
    if trace_path.is_file():
        lines = [line for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        report["impulse_trace"] = {
            "path": str(trace_path.name),
            "rows": len(lines),
            "last": json.loads(lines[-1]) if lines else None,
        }
    else:
        report["impulse_trace"] = {"path": str(trace_path.name), "rows": 0}
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
