#!/usr/bin/env python3
"""Agent duplex wire — JSONL inbox/outbox for Cursor agent ↔ Neumann (ADR-0028 L4 host).

Not interactive stdin: agent peripheral appends outbox lines; bridge enqueues partner_text
afferent, waits efferent, and drains partner initiative into inbox while life reactor runs.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

_AGENT_DIR = Path("body") / "text" / "agent"
_OUTBOX_NAME = "outbox.jsonl"
_INBOX_NAME = "inbox.jsonl"
_PULSE_NAME = "bridge_pulse.json"
_CURSOR_NAME = "cursor.json"

_OUTBOX_PROCESSING_STALE_S = 150.0
_OUTBOX_PROCESSING_ERROR_S = 600.0
_BRIDGE_PULSE_TURN_S = 6.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def agent_wire_dir(store_dir: Path, *, create: bool = False) -> Path:
    path = store_dir.resolve() / _AGENT_DIR
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def outbox_path(store_dir: Path) -> Path:
    return agent_wire_dir(store_dir) / _OUTBOX_NAME


def inbox_path(store_dir: Path) -> Path:
    return agent_wire_dir(store_dir) / _INBOX_NAME


def bridge_pulse_path(store_dir: Path) -> Path:
    return agent_wire_dir(store_dir) / _PULSE_NAME


def cursor_path(store_dir: Path) -> Path:
    return agent_wire_dir(store_dir) / _CURSOR_NAME


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


def _atomic_append_line(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _rewrite_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    body = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    tmp.write_text(body, encoding="utf-8")
    tmp.replace(path)


Direction = Literal["reply", "initiative", "error"]


def _iso_age_s(iso: str) -> float | None:
    if not iso:
        return None
    try:
        ts = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - ts).total_seconds()
    except ValueError:
        return None


def reclaim_stale_outbox(
    store_dir: Path,
    *,
    stale_s: float = _OUTBOX_PROCESSING_STALE_S,
    error_after_s: float = _OUTBOX_PROCESSING_ERROR_S,
) -> list[str]:
    """Reset orphaned processing rows — bridge died mid-turn."""
    rows = _read_jsonl(outbox_path(store_dir))
    if not rows:
        return []
    changed: list[str] = []
    updated: list[dict[str, Any]] = []
    for row in rows:
        status = str(row.get("status") or "pending")
        if status != "processing":
            updated.append(row)
            continue
        age = _iso_age_s(str(row.get("claimed_at") or row.get("enqueued_at") or ""))
        req_id = str(row.get("id") or "")
        if age is None:
            updated.append(row)
            continue
        if age >= error_after_s:
            updated.append({**row, "status": "error", "completed_at": _utc_now(), "error": "stale_processing"})
            changed.append(req_id)
        elif age >= stale_s:
            updated.append({**row, "status": "pending", "reclaimed_at": _utc_now()})
            changed.append(req_id)
        else:
            updated.append(row)
    if changed:
        _rewrite_jsonl(outbox_path(store_dir), updated)
    return changed


def outbox_in_flight(store_dir: Path) -> dict[str, Any] | None:
    for row in _read_jsonl(outbox_path(store_dir)):
        if str(row.get("status") or "") == "processing":
            return row
    return None


def find_inbox_reply(store_dir: Path, request_id: str) -> dict[str, Any] | None:
    for row in read_inbox(store_dir, limit=128):
        if str(row.get("request_id") or "") != request_id:
            continue
        if str(row.get("direction") or "") in ("reply", "error"):
            return row
    return None


def write_bridge_pulse(store_dir: Path, *, extra: dict[str, Any] | None = None) -> None:
    import time

    payload: dict[str, Any] = {
        "pid": os.getpid(),
        "holder": "partner_agent_wire",
        "updated_at": _utc_now(),
    }
    if extra:
        payload.update(extra)
    path = bridge_pulse_path(store_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for attempt in range(8):
        try:
            tmp.replace(path)
            return
        except PermissionError:
            if attempt >= 7:
                raise
            time.sleep(0.05 * (attempt + 1))


def bridge_alive(store_dir: Path, *, max_age_s: float = _BRIDGE_PULSE_TURN_S) -> bool:
    path = bridge_pulse_path(store_dir)
    if not path.is_file():
        return False
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(raw, dict):
        return False
    pid = int(raw.get("pid") or 0)
    if pid and not _pid_alive(pid):
        return False
    phase = str(raw.get("phase") or "")
    if phase in ("waiting_efferent", "processing_turn") and pid:
        return True
    updated = str(raw.get("updated_at") or "")
    if not updated:
        return False
    age = _iso_age_s(updated)
    if age is None:
        return False
    return age <= max_age_s


def try_claim_bridge(store_dir: Path) -> bool:
    """Single bridge instance per store — refuse if another live pid holds pulse."""
    path = bridge_pulse_path(store_dir)
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = None
        if isinstance(raw, dict):
            other = int(raw.get("pid") or 0)
            if other and other != os.getpid() and _pid_alive(other):
                age = _iso_age_s(str(raw.get("updated_at") or ""))
                if age is not None and age <= max(_BRIDGE_PULSE_TURN_S, 30.0):
                    return False
    write_bridge_pulse(store_dir, extra={"phase": "bridge_start"})
    return True


def enqueue_agent_outbox(
    store_dir: Path,
    text: str,
    *,
    kind: str = "chat",
    provenance: dict[str, Any] | None = None,
) -> str:
    text = (text or "").strip()
    if not text:
        raise ValueError("empty agent outbox text")
    req_id = uuid.uuid4().hex[:12]
    _atomic_append_line(
        outbox_path(store_dir),
        {
            "id": req_id,
            "text": text,
            "kind": str(kind or "chat"),
            "provenance": dict(provenance or {}),
            "status": "pending",
            "enqueued_at": _utc_now(),
        },
    )
    return req_id


def drain_pending_outbox(store_dir: Path, *, limit: int = 1) -> list[dict[str, Any]]:
    reclaim_stale_outbox(store_dir)
    rows = _read_jsonl(outbox_path(store_dir))
    if not rows:
        return []
    if outbox_in_flight(store_dir):
        return []
    out: list[dict[str, Any]] = []
    now = _utc_now()
    updated: list[dict[str, Any]] = []
    n = 0
    cap = max(1, limit)
    for row in rows:
        if str(row.get("status") or "pending") == "pending" and n < cap:
            claimed = {**row, "status": "processing", "claimed_at": now}
            out.append(claimed)
            updated.append(claimed)
            n += 1
        else:
            updated.append(row)
    if out:
        _rewrite_jsonl(outbox_path(store_dir), updated)
    return out


def mark_outbox_done(store_dir: Path, req_id: str, *, status: str = "done") -> None:
    rows = _read_jsonl(outbox_path(store_dir))
    if not rows:
        return
    now = _utc_now()
    updated: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("id")) == req_id:
            updated.append({**row, "status": status, "completed_at": now})
        else:
            updated.append(row)
    _rewrite_jsonl(outbox_path(store_dir), updated)


def append_agent_inbox(
    store_dir: Path,
    *,
    direction: Direction,
    text: str,
    request_id: str | None = None,
    kind: str | None = None,
    provenance: dict[str, Any] | None = None,
    tick: int | None = None,
) -> str:
    text = (text or "").strip()
    if not text and direction != "error":
        raise ValueError("empty inbox text")
    msg_id = uuid.uuid4().hex[:12]
    row: dict[str, Any] = {
        "id": msg_id,
        "direction": direction,
        "speaker": "neumann",
        "text": text,
        "at": _utc_now(),
    }
    if request_id:
        row["request_id"] = request_id
    if kind:
        row["kind"] = kind
    if tick is not None:
        row["tick"] = int(tick)
    if provenance:
        row["provenance"] = provenance
    _atomic_append_line(inbox_path(store_dir), row)
    return msg_id


def read_inbox(
    store_dir: Path,
    *,
    after_id: str | None = None,
    limit: int = 32,
) -> list[dict[str, Any]]:
    rows = _read_jsonl(inbox_path(store_dir))
    if not rows:
        return []
    if after_id:
        ids = [str(r.get("id") or "") for r in rows]
        if after_id in ids:
            idx = ids.index(after_id)
            rows = rows[idx + 1 :]
    return rows[-max(1, limit) :]


def wait_inbox_reply(
    store_dir: Path,
    request_id: str,
    *,
    timeout_s: float = 120.0,
    poll_s: float = 0.12,
    on_poll: Callable[[], None] | None = None,
) -> dict[str, Any]:
    import time

    deadline = time.monotonic() + max(1.0, timeout_s)
    seen: set[str] = set()
    while time.monotonic() < deadline:
        existing = find_inbox_reply(store_dir, request_id)
        if existing is not None:
            return existing
        for row in read_inbox(store_dir, limit=64):
            rid = str(row.get("id") or "")
            if rid in seen:
                continue
            seen.add(rid)
            if str(row.get("request_id") or "") != request_id:
                continue
            if str(row.get("direction") or "") in ("reply", "error"):
                return row
        if on_poll is not None:
            on_poll()
        time.sleep(poll_s)
    reclaim_stale_outbox(store_dir)
    raise TimeoutError(f"agent inbox reply timeout for request {request_id}")


def read_cursor(store_dir: Path) -> str | None:
    path = cursor_path(store_dir)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(raw, dict):
        last = str(raw.get("last_inbox_id") or "").strip()
        return last or None
    return None


def write_cursor(store_dir: Path, last_inbox_id: str) -> None:
    path = cursor_path(store_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(
        json.dumps({"last_inbox_id": last_inbox_id, "updated_at": _utc_now()}, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)
