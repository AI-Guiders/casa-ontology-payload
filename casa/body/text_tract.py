#!/usr/bin/env python3
"""Partner text tract — symbolic afferent / efferent body organ (ADR-0028 + ADR-0046).

Not audio: partner lines **afferent** (как ручка принимает давление партнёра на бумагу),
subject lines **efferent**. `tract_id: partner_text`, `tract_kind: symbolic`.
Store: `body/text/`. Host peripherals (console chat) — L4 wire only.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

PARTNER_TEXT_TRACT_ID = "partner_text"
TRACT_KIND_SYMBOLIC = "symbolic"
DIRECTION_AFFERENT: Literal["afferent"] = "afferent"
DIRECTION_EFFERENT: Literal["efferent"] = "efferent"

AFFERENT_FUNCTION = f"body.tract.{PARTNER_TEXT_TRACT_ID}.afferent"
EFFERENT_FUNCTION = f"body.tract.{PARTNER_TEXT_TRACT_ID}.efferent"
TEXT_WIRE_CONSOLE = "console"

_CUE_NAME = "cue.json"
_PULSE_NAME = "pulse.json"
_BODY_TEXT_DIR = Path("body") / "text"
_CUE_STALE_S = 180.0
_DEFAULT_PULSE_STALE_S = 8.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def text_dir(store_dir: Path, *, create: bool = False) -> Path:
    """Partner text tract buffer in agent store."""
    path = store_dir.resolve() / _BODY_TEXT_DIR
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def cue_path(store_dir: Path) -> Path:
    return text_dir(store_dir) / _CUE_NAME


def pulse_path(store_dir: Path) -> Path:
    return text_dir(store_dir) / _PULSE_NAME


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


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


def read_pulse(store_dir: Path) -> dict[str, Any] | None:
    return _read_json(pulse_path(store_dir))


def write_pulse(
    store_dir: Path,
    *,
    macro_tick: int,
    sn_mode: str | None = None,
    holder: str = "life_reactor",
    extra: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "pid": os.getpid(),
        "holder": holder,
        "tract_id": PARTNER_TEXT_TRACT_ID,
        "tract_kind": TRACT_KIND_SYMBOLIC,
        "macro_tick": macro_tick,
        "sn_mode": sn_mode,
        "updated_at": _utc_now(),
    }
    if extra:
        payload.update(extra)
    _atomic_write_json(pulse_path(store_dir), payload)


def reactor_alive(store_dir: Path, *, max_age_s: float = _DEFAULT_PULSE_STALE_S) -> bool:
    pulse = read_pulse(store_dir)
    if not pulse:
        return False
    pid = int(pulse.get("pid") or 0)
    if pid and not _pid_alive(pid):
        return False
    updated = str(pulse.get("updated_at") or "")
    if not updated:
        return False
    try:
        ts = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - ts).total_seconds()
    except ValueError:
        return False
    return age <= max_age_s


def read_afferent_cue(store_dir: Path) -> dict[str, Any] | None:
    cue = _read_json(cue_path(store_dir))
    if not cue:
        return None
    status = str(cue.get("status") or "pending")
    if status == "pending":
        enqueued = str(cue.get("enqueued_at") or "")
        if enqueued:
            try:
                ts = datetime.fromisoformat(enqueued.replace("Z", "+00:00"))
                if (datetime.now(timezone.utc) - ts).total_seconds() > _CUE_STALE_S:
                    cue["status"] = "stale"
            except ValueError:
                pass
    return cue


def enqueue_afferent(
    store_dir: Path,
    text: str,
    *,
    kind: str = "chat",
    wire: str = TEXT_WIRE_CONSOLE,
) -> str:
    """Afferent: partner text into symbolic tract (host peripheral)."""
    text = text.strip()
    if not text:
        raise ValueError("empty afferent cue")
    existing = read_afferent_cue(store_dir)
    if existing and str(existing.get("status")) == "pending":
        raise TimeoutError(f"partner_text tract busy: {existing.get('id')}")
    cue_id = uuid.uuid4().hex[:12]
    payload = {
        "id": cue_id,
        "text": text,
        "kind": kind,
        "wire": wire,
        "tract_id": PARTNER_TEXT_TRACT_ID,
        "tract_kind": TRACT_KIND_SYMBOLIC,
        "direction": DIRECTION_AFFERENT,
        "function_id": AFFERENT_FUNCTION,
        "status": "pending",
        "enqueued_at": _utc_now(),
    }
    _atomic_write_json(cue_path(store_dir), payload)
    return cue_id


def complete_efferent(
    store_dir: Path,
    cue_id: str,
    *,
    reply_text: str,
    tick: int | None = None,
    report: dict[str, Any] | None = None,
) -> None:
    """Efferent: subject text on tract for host peripheral."""
    cue = read_afferent_cue(store_dir) or {}
    if str(cue.get("id")) != cue_id:
        return
    cue["status"] = "done"
    cue["completed_at"] = _utc_now()
    cue["reply_text"] = reply_text
    cue["direction"] = DIRECTION_EFFERENT
    cue["function_id"] = EFFERENT_FUNCTION
    if tick is not None:
        cue["tick"] = tick
    if report is not None:
        cue["report_hint"] = {
            "sn_mode": report.get("sn_mode"),
            "wall_ms": report.get("wall_ms"),
        }
    _atomic_write_json(cue_path(store_dir), cue)


def fail_afferent_cue(store_dir: Path, cue_id: str, *, error: str) -> None:
    cue = read_afferent_cue(store_dir) or {}
    if str(cue.get("id")) != cue_id:
        return
    cue["status"] = "error"
    cue["completed_at"] = _utc_now()
    cue["error"] = error
    _atomic_write_json(cue_path(store_dir), cue)


def wait_for_efferent(
    store_dir: Path,
    cue_id: str,
    *,
    timeout_s: float = 120.0,
    poll_s: float = 0.15,
    on_life_tick: Callable[[int, dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Host peripheral waits for efferent reply after afferent enqueue."""
    deadline = time.monotonic() + max(1.0, timeout_s)
    last_life_t: int | None = None
    while time.monotonic() < deadline:
        if on_life_tick is not None:
            pulse = read_pulse(store_dir)
            if pulse and pulse.get("macro_tick") is not None:
                life_t = int(pulse["macro_tick"])
                if last_life_t != life_t:
                    on_life_tick(life_t, pulse)
                    last_life_t = life_t
        cue = read_afferent_cue(store_dir)
        if cue and str(cue.get("id")) == cue_id:
            status = str(cue.get("status") or "")
            if status == "done":
                return cue
            if status == "error":
                raise RuntimeError(str(cue.get("error") or "partner_text tick failed"))
        time.sleep(poll_s)
    raise TimeoutError(f"efferent reply timeout for cue {cue_id}")


def extract_dialogue_reply(report: dict[str, Any]) -> str:
    dialogue = report.get("dialogue") or {}
    reply = str(dialogue.get("reply_text") or "").strip()
    if not reply and dialogue.get("outbound"):
        reply = str(dialogue["outbound"][-1].get("text") or "").strip()
    if reply:
        return reply
    if dialogue.get("soft_miss"):
        return "(пока не могу собрать ответ)"
    return "(молчит)"


def poll_pending_afferent(store_dir: Path) -> dict[str, Any] | None:
    """Life reactor: pending afferent partner text."""
    cue = read_afferent_cue(store_dir)
    if cue and str(cue.get("status")) == "pending":
        return cue
    return None


# Stable names used by dialogue / host wire
read_partner_cue = read_afferent_cue
enqueue_partner_cue = enqueue_afferent
complete_partner_cue = complete_efferent
fail_partner_cue = fail_afferent_cue
wait_for_partner_reply = wait_for_efferent
poll_pending_read = poll_pending_afferent
partner_dir = text_dir

# ADR-0028 direction aliases (older import paths)
TEXT_FUNCTION_READ = AFFERENT_FUNCTION
TEXT_FUNCTION_WRITE = EFFERENT_FUNCTION
