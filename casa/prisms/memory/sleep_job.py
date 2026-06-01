#!/usr/bin/env python3
"""SleepJob scheduler state (CASA-ADR-0023 S1–S2, R6)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sleep_job(state: dict) -> dict[str, Any]:
    cons = state.setdefault("consolidation", {})
    job = cons.get("sleep_job")
    if not isinstance(job, dict):
        job = {
            "batch_index": 0,
            "pending_count": 0,
            "interrupted_at": None,
            "last_batch_at": None,
        }
        cons["sleep_job"] = job
    return job


def note_sleep_batch(
    state: dict,
    *,
    pending_after: int,
    merged: int,
    max_episodes: int | None,
) -> dict[str, Any]:
    job = sleep_job(state)
    job["batch_index"] = int(job.get("batch_index") or 0) + 1
    job["pending_count"] = pending_after
    job["last_batch_at"] = _utc_now()
    job["last_merged"] = merged
    job["last_max_episodes"] = max_episodes
    if pending_after == 0:
        job["interrupted_at"] = None
    return job


def request_sleep_interrupt(state: dict, *, reason: str = "wake") -> None:
    job = sleep_job(state)
    job["interrupted_at"] = _utc_now()
    job["interrupt_reason"] = reason


def clear_sleep_interrupt(state: dict) -> None:
    job = sleep_job(state)
    job["interrupted_at"] = None
    job.pop("interrupt_reason", None)


def sleep_job_should_yield(state: dict) -> bool:
    """Cooperative yield: wake mode or explicit interrupt between batches."""
    job = sleep_job(state)
    if job.get("interrupted_at"):
        return True
    sn = state.get("sn") or {}
    if str(sn.get("mode") or "wake") == "wake" and bool(sn.get("input_pending")):
        return True
    return False
