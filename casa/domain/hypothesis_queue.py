#!/usr/bin/env python3
"""Hypothesis queue — predict → verify → close/revise (ADR-0036)."""

from __future__ import annotations

import hashlib
from typing import Any

DEFAULT_TTL_TICKS = 12
MAX_QUEUE = 32


def _queue(state: dict) -> list[dict[str, Any]]:
    raw = state.setdefault("hypothesis_queue", [])
    return raw if isinstance(raw, list) else []


def _hid(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def enqueue_hypothesis(
    state: dict,
    *,
    expect: str,
    concept_id: str = "",
    tick: int,
    ttl_ticks: int = DEFAULT_TTL_TICKS,
    source: str = "check",
) -> dict[str, Any]:
    text = str(expect or "").strip()
    if not text:
        return {}
    q = _queue(state)
    hid = _hid(f"{concept_id}:{text}")
    for row in q:
        if row.get("id") == hid and row.get("status") == "open":
            row["last_tick"] = tick
            return row

    entry = {
        "id": hid,
        "expect": text,
        "concept_id": str(concept_id or ""),
        "status": "open",
        "created_tick": tick,
        "last_tick": tick,
        "ttl_ticks": ttl_ticks,
        "source": source,
        "outcome": None,
    }
    q.append(entry)
    state["hypothesis_queue"] = q[-MAX_QUEUE:]
    return entry


def verify_hypothesis(
    state: dict,
    *,
    concept_id: str,
    passed: bool,
    tick: int,
) -> list[dict[str, Any]]:
    cid = str(concept_id or "").strip()
    closed: list[dict[str, Any]] = []
    q = _queue(state)
    for row in q:
        if row.get("status") != "open":
            continue
        if cid and row.get("concept_id") and row.get("concept_id") != cid:
            continue
        age = tick - int(row.get("created_tick") or tick)
        if age > int(row.get("ttl_ticks") or DEFAULT_TTL_TICKS):
            row["status"] = "expired"
            row["outcome"] = "ttl"
            closed.append(row)
            continue
        row["status"] = "closed"
        row["outcome"] = "pass" if passed else "fail"
        row["last_tick"] = tick
        closed.append(row)
    state["hypothesis_queue"] = q
    return closed


def open_hypothesis_count(state: dict) -> int:
    return sum(1 for row in _queue(state) if row.get("status") == "open")


def prune_hypothesis_queue(state: dict, *, tick: int) -> int:
    q = _queue(state)
    kept: list[dict[str, Any]] = []
    removed = 0
    for row in q:
        if row.get("status") != "open":
            if row.get("status") in ("closed", "expired"):
                removed += 1
                continue
        age = tick - int(row.get("last_tick") or row.get("created_tick") or tick)
        ttl = int(row.get("ttl_ticks") or DEFAULT_TTL_TICKS)
        if row.get("status") == "open" and age > ttl * 2:
            removed += 1
            continue
        kept.append(row)
    state["hypothesis_queue"] = kept[-MAX_QUEUE:]
    return removed


def hypothesis_from_check(
    state: dict,
    *,
    cue: str,
    concept_id: str,
    passed: bool,
    tick: int,
) -> dict[str, Any]:
    """Check hook: enqueue on fail, verify on pass."""
    if passed:
        closed = verify_hypothesis(state, concept_id=concept_id, passed=True, tick=tick)
        return {"verified": closed}
    expect = f"cue «{cue}» resolves {concept_id or 'goal'} without surprise"
    entry = enqueue_hypothesis(
        state,
        expect=expect,
        concept_id=concept_id,
        tick=tick,
        source="surprise",
    )
    return {"enqueued": entry}
