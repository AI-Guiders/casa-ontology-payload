#!/usr/bin/env python3
"""Motor speech tract — efferent phonation cue (ADR-0082 + ADR-0028).

Not TTS: host peripheral receives motor unit plan; acoustic feedback re-enters via
auditory self-imprint. `tract_id: motor_speech`, `tract_kind: motor`.
Store: `body/speech/`.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from casa.domain.motor_speech_plan import MotorSpeechPlan

MOTOR_SPEECH_TRACT_ID = "motor_speech"
TRACT_KIND_MOTOR = "motor"
DIRECTION_EFFERENT: Literal["efferent"] = "efferent"

EFFERENT_FUNCTION = f"body.tract.{MOTOR_SPEECH_TRACT_ID}.efferent"

_CUE_NAME = "cue.json"
_PULSE_NAME = "pulse.json"
_BODY_SPEECH_DIR = Path("body") / "speech"
_CUE_STALE_S = 180.0
_DEFAULT_PULSE_STALE_S = 8.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def speech_dir(store_dir: Path, *, create: bool = False) -> Path:
    path = store_dir.resolve() / _BODY_SPEECH_DIR
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def cue_path(store_dir: Path) -> Path:
    return speech_dir(store_dir) / _CUE_NAME


def pulse_path(store_dir: Path) -> Path:
    return speech_dir(store_dir) / _PULSE_NAME


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
        "tract_id": MOTOR_SPEECH_TRACT_ID,
        "tract_kind": TRACT_KIND_MOTOR,
        "macro_tick": macro_tick,
        "sn_mode": sn_mode,
        "updated_at": _utc_now(),
    }
    if extra:
        payload.update(extra)
    _atomic_write_json(pulse_path(store_dir), payload)


def read_efferent_cue(store_dir: Path) -> dict[str, Any] | None:
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


def enqueue_efferent_plan(
    store_dir: Path,
    plan: MotorSpeechPlan,
    *,
    wire: str = "stub_vocoder",
) -> str:
    """Efferent: motor unit plan for L4 peripheral (stub or hardware)."""
    speech_dir(store_dir, create=True)
    payload = {
        "id": plan.plan_id,
        "plan_id": plan.plan_id,
        "units": list(plan.units),
        "intent": plan.intent,
        "tick": plan.tick,
        "scene_id": plan.scene_id,
        "wire": wire,
        "tract_id": MOTOR_SPEECH_TRACT_ID,
        "tract_kind": TRACT_KIND_MOTOR,
        "direction": DIRECTION_EFFERENT,
        "function_id": EFFERENT_FUNCTION,
        "status": "pending",
        "enqueued_at": _utc_now(),
    }
    _atomic_write_json(cue_path(store_dir), payload)
    return plan.plan_id


def complete_efferent_plan(
    store_dir: Path,
    plan_id: str,
    *,
    heard_window_id: str | None = None,
    report: dict[str, Any] | None = None,
) -> None:
    cue = read_efferent_cue(store_dir) or {}
    if str(cue.get("plan_id") or cue.get("id")) != plan_id:
        return
    cue["status"] = "done"
    cue["completed_at"] = _utc_now()
    if heard_window_id:
        cue["heard_window_id"] = heard_window_id
    if report is not None:
        cue["report_hint"] = {
            "self_listen": report.get("self_listen"),
            "motor_bind": report.get("motor_bind"),
        }
    _atomic_write_json(cue_path(store_dir), cue)


def poll_pending_efferent(store_dir: Path) -> dict[str, Any] | None:
    cue = read_efferent_cue(store_dir)
    if cue and str(cue.get("status")) == "pending":
        return cue
    return None
