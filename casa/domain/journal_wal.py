#!/usr/bin/env python3
"""Journal WAL — durable narrative append before entries.jsonl commit (ADR-0040)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from casa.prisms.shared.field_write import _write_json
from casa.prisms.shared.store_layout import journal_entries_path, journal_root

WAL_SCHEMA_VERSION = 1
WAL_NAME = "wal.log"
CHECKPOINT_NAME = "checkpoint.json"


def wal_path(store_dir: Path) -> Path:
    return journal_root(store_dir) / WAL_NAME


def checkpoint_path(store_dir: Path) -> Path:
    return journal_root(store_dir) / CHECKPOINT_NAME


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fsync_file(path: Path) -> None:
    if not path.is_file():
        return
    with open(path, "r+b") as fh:
        fh.flush()
        os.fsync(fh.fileno())


def _append_line(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            doc = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(doc, dict):
            rows.append(doc)
    return rows


def load_checkpoint(store_dir: Path) -> dict[str, Any]:
    path = checkpoint_path(store_dir)
    if not path.is_file():
        return {"schema_version": WAL_SCHEMA_VERSION, "domains": {}}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": WAL_SCHEMA_VERSION, "domains": {}}
    if not isinstance(doc, dict):
        return {"schema_version": WAL_SCHEMA_VERSION, "domains": {}}
    doc.setdefault("schema_version", WAL_SCHEMA_VERSION)
    doc.setdefault("domains", {})
    return doc


def save_checkpoint(store_dir: Path, checkpoint: dict[str, Any]) -> None:
    checkpoint["schema_version"] = WAL_SCHEMA_VERSION
    _write_json(checkpoint_path(store_dir), checkpoint)


def peek_field_version(store_dir: Path) -> int:
    try:
        from casa.domain.agent_field import field_db_stats

        stats = field_db_stats(store_dir)
        if stats.get("ok") and stats.get("field_version") is not None:
            return int(stats["field_version"])
    except Exception:
        pass
    fs = store_dir / "field_state.json"
    if fs.is_file():
        try:
            doc = json.loads(fs.read_text(encoding="utf-8"))
            return int(doc.get("field_version") or 0)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    return 0


def _next_seq(checkpoint: dict[str, Any], domain: str) -> int:
    domains = checkpoint.get("domains") or {}
    dom = domains.get(domain) or {}
    return int(dom.get("last_seq") or 0) + 1


def wal_append_pending(
    store_dir: Path,
    domain: str,
    entry: dict[str, Any],
    *,
    field_version: int | None = None,
) -> int:
    """Stage append intent in wal.log; return seq."""
    store_dir = store_dir.resolve()
    checkpoint = load_checkpoint(store_dir)
    seq = _next_seq(checkpoint, domain)
    fv = int(field_version if field_version is not None else peek_field_version(store_dir))
    _append_line(
        wal_path(store_dir),
        {
            "schema_version": WAL_SCHEMA_VERSION,
            "op": "append",
            "seq": seq,
            "domain": domain,
            "field_version": fv,
            "entry_id": str(entry.get("id") or ""),
            "at": _utc_now(),
            "entry": entry,
        },
    )
    return seq


def wal_commit_append(
    store_dir: Path,
    domain: str,
    seq: int,
    entry: dict[str, Any],
    *,
    field_version: int | None = None,
) -> None:
    """Mark wal append committed; advance checkpoint."""
    store_dir = store_dir.resolve()
    fv = int(field_version if field_version is not None else peek_field_version(store_dir))
    entry_id = str(entry.get("id") or "")
    _append_line(
        wal_path(store_dir),
        {
            "schema_version": WAL_SCHEMA_VERSION,
            "op": "commit",
            "seq": seq,
            "domain": domain,
            "field_version": fv,
            "entry_id": entry_id,
            "at": _utc_now(),
        },
    )

    checkpoint = load_checkpoint(store_dir)
    domains = checkpoint.setdefault("domains", {})
    dom = domains.setdefault(domain, {})
    dom["last_seq"] = seq
    dom["last_entry_id"] = entry_id
    dom["field_version"] = fv
    dom["entry_count"] = int(dom.get("entry_count") or 0) + 1
    dom["updated_at"] = _utc_now()
    save_checkpoint(store_dir, checkpoint)
    if not _pending_from_wal(_read_jsonl(wal_path(store_dir))):
        wal_path(store_dir).unlink(missing_ok=True)


def append_entry_line(store_dir: Path, domain: str, entry: dict[str, Any]) -> None:
    """Atomic append one JSONL line to domain entries."""
    path = journal_entries_path(store_dir, domain)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n"
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())


def load_entries_safe(store_dir: Path, domain: str) -> list[dict[str, Any]]:
    """Load entries; drop trailing corrupt JSONL lines."""
    path = journal_entries_path(store_dir, domain)
    if not path.is_file():
        return []
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    rows: list[dict[str, Any]] = []
    good_lines: list[str] = []
    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            doc = json.loads(stripped)
        except json.JSONDecodeError:
            break
        if isinstance(doc, dict):
            rows.append(doc)
            good_lines.append(stripped)
    if len(good_lines) < len([ln for ln in raw_lines if ln.strip()]):
        text = "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in rows)
        path.write_text(text, encoding="utf-8")
    return rows


def _pending_from_wal(wal_rows: list[dict[str, Any]]) -> dict[tuple[str, int], dict[str, Any]]:
    pending: dict[tuple[str, int], dict[str, Any]] = {}
    for row in wal_rows:
        op = str(row.get("op") or "")
        domain = str(row.get("domain") or "")
        seq = int(row.get("seq") or 0)
        key = (domain, seq)
        if op == "append":
            pending[key] = row
        elif op == "commit" and key in pending:
            pending.pop(key, None)
    return pending


def _compact_wal(store_dir: Path, pending: dict[tuple[str, int], dict[str, Any]]) -> None:
    path = wal_path(store_dir)
    if not pending:
        if path.is_file():
            path.unlink(missing_ok=True)
        return
    lines = []
    for (_domain, _seq), row in sorted(pending.items(), key=lambda x: x[0][1]):
        lines.append(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    _fsync_file(path)


def replay_journal_wal(store_dir: Path) -> dict[str, Any]:
    """Cold boot: replay uncommitted wal appends; repair truncated entries.jsonl."""
    from casa.prisms.control.fpn_state import read_session_meta, write_session_meta

    store_dir = store_dir.resolve()
    at = _utc_now()
    wal_rows = _read_jsonl(wal_path(store_dir))
    pending = _pending_from_wal(wal_rows)
    replayed: list[str] = []
    skipped: list[str] = []

    for (domain, _seq), row in list(pending.items()):
        entry = row.get("entry")
        if not isinstance(entry, dict):
            pending.pop((domain, _seq), None)
            continue
        entry_id = str(entry.get("id") or "")
        existing = load_entries_safe(store_dir, domain)
        ids = {str(r.get("id") or "") for r in existing}
        if entry_id and entry_id in ids:
            skipped.append(entry_id)
            pending.pop((domain, _seq), None)
            continue
        append_entry_line(store_dir, domain, entry)
        replayed.append(entry_id or f"{domain}:{_seq}")

    _compact_wal(store_dir, pending)

    report: dict[str, Any] = {
        "schema_version": WAL_SCHEMA_VERSION,
        "tool": "journal_wal_replay",
        "at": at,
        "replayed": replayed,
        "skipped_existing": skipped,
        "pending_left": len(pending),
        "recovered": bool(replayed or skipped),
    }
    if report["recovered"]:
        meta = read_session_meta(store_dir)
        meta["last_journal_wal_replay_at"] = at
        meta["last_journal_wal_replayed"] = len(replayed)
        write_session_meta(store_dir, meta)
    return report


def recovery_warnings_from_session(store_dir: Path) -> list[str]:
    from casa.prisms.control.fpn_state import read_session_meta

    meta = read_session_meta(store_dir)
    warnings: list[str] = []
    if meta.get("last_journal_wal_replay_at") and int(meta.get("last_journal_wal_replayed") or 0) > 0:
        warnings.append("journal_wal_replayed")
    if wal_path(store_dir).is_file():
        pending = _pending_from_wal(_read_jsonl(wal_path(store_dir)))
        if pending:
            warnings.append("journal_wal_pending")
    return warnings
