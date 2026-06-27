#!/usr/bin/env python3
"""Episodic wake index: moment_id, episode_id, boundaries (ADR-0088 hippo_wake)."""

from __future__ import annotations

import re
from typing import Any

from casa.prisms.hippo.mode import HIPPO_MODE_WAKE, set_hippo_mode

HIPPO_INDEX_KEY = "hippo_index"
HIPPO_INDEX_SCHEMA_VERSION = 1


def ensure_hippo_index(state: dict[str, Any]) -> dict[str, Any]:
    """Ensure ``state[hippo_index]`` exists; return the index dict."""
    raw = state.get(HIPPO_INDEX_KEY)
    if isinstance(raw, dict) and int(raw.get("schema_version") or 0) == HIPPO_INDEX_SCHEMA_VERSION:
        idx = raw
    else:
        idx = {
            "schema_version": HIPPO_INDEX_SCHEMA_VERSION,
            "next_moment_seq": 0,
            "next_episode_seq": 0,
            "active_episode_id": None,
            "active_moment_id": None,
            "active_scene_id": None,
            "active_beat_id": None,
            "moment_buffer": {},
            "journal": [],
        }
        state[HIPPO_INDEX_KEY] = idx
    idx.setdefault("moment_buffer", {})
    idx.setdefault("journal", [])
    return idx


def _slug(s: str, *, max_len: int = 48) -> str:
    raw = re.sub(r"[^a-z0-9]+", "-", str(s or "").strip().lower())
    raw = raw.strip("-") or "scene"
    return raw[:max_len]


def _next_moment_id(idx: dict[str, Any]) -> str:
    seq = int(idx.get("next_moment_seq") or 0) + 1
    idx["next_moment_seq"] = seq
    return f"mom-{seq:06d}"


def _next_episode_id(idx: dict[str, Any], *, scene_id: str | None = None) -> str:
    seq = int(idx.get("next_episode_seq") or 0) + 1
    idx["next_episode_seq"] = seq
    if scene_id:
        return f"epi-{_slug(scene_id)}-{seq:04d}"
    return f"epi-{seq:06d}"


def _journal(
    idx: dict[str, Any],
    *,
    event: str,
    reason: str = "",
    moment_id: str | None = None,
    episode_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    row: dict[str, Any] = {"event": event}
    if reason:
        row["reason"] = reason
    if moment_id:
        row["moment_id"] = moment_id
    if episode_id:
        row["episode_id"] = episode_id
    if extra:
        row.update(extra)
    journal = idx.setdefault("journal", [])
    journal.append(row)


def close_moment_boundary(state: dict[str, Any], *, reason: str) -> dict[str, Any] | None:
    """Close active moment; flush buffer entry to journal. Returns closed moment id."""
    idx = ensure_hippo_index(state)
    moment_id = idx.get("active_moment_id")
    if not moment_id:
        return None
    buffer = idx.get("moment_buffer") or {}
    snapshot = buffer.pop(moment_id, None)
    idx["active_moment_id"] = None
    idx["active_beat_id"] = None
    _journal(
        idx,
        event="moment_closed",
        reason=reason,
        moment_id=str(moment_id),
        episode_id=str(idx.get("active_episode_id") or "") or None,
        extra={"snapshot": snapshot} if snapshot else None,
    )
    return {"moment_id": moment_id, "reason": reason, "snapshot": snapshot}


def close_episode_boundary(state: dict[str, Any], *, reason: str) -> dict[str, Any]:
    """Close active moment (if any) and episode; start clean episode span."""
    closed_moment = close_moment_boundary(state, reason=f"episode:{reason}")
    idx = ensure_hippo_index(state)
    episode_id = idx.get("active_episode_id")
    if not episode_id:
        return {"closed": False, "reason": reason, "closed_moment": closed_moment}
    idx["active_episode_id"] = None
    idx["active_scene_id"] = None
    _journal(
        idx,
        event="episode_closed",
        reason=reason,
        episode_id=str(episode_id),
        extra={"closed_moment": closed_moment["moment_id"] if closed_moment else None},
    )
    return {
        "closed": True,
        "episode_id": episode_id,
        "reason": reason,
        "closed_moment": closed_moment,
    }


def _open_episode(idx: dict[str, Any], *, scene_id: str) -> str:
    episode_id = _next_episode_id(idx, scene_id=scene_id)
    idx["active_episode_id"] = episode_id
    idx["active_scene_id"] = scene_id
    _journal(idx, event="episode_opened", reason="scene", episode_id=episode_id, extra={"scene_id": scene_id})
    return episode_id


def _open_moment(idx: dict[str, Any], *, beat_id: str | None, scene_id: str) -> str:
    moment_id = _next_moment_id(idx)
    idx["active_moment_id"] = moment_id
    idx["active_beat_id"] = beat_id
    idx.setdefault("moment_buffer", {})[moment_id] = {
        "scene_id": scene_id,
        "beat_id": beat_id,
        "modalities": [],
    }
    _journal(
        idx,
        event="moment_opened",
        reason="beat" if beat_id else "tick",
        moment_id=moment_id,
        episode_id=str(idx.get("active_episode_id") or "") or None,
        extra={"beat_id": beat_id, "scene_id": scene_id},
    )
    return moment_id


def hippo_wake_index_tick(
    state: dict[str, Any],
    *,
    scene_id: str,
    beat_id: str | None = None,
    stream_id: str | None = None,
    seq: int | None = None,
    visual_delta: float | None = None,
    coactive: bool = False,
    affect_snapshot: dict[str, Any] | None = None,
    modality_tags: list[str] | None = None,
    record_tick: bool = True,
) -> dict[str, Any]:
    """Index one life-tick into episodic wake buffer (ADR-0088 R2 slice 0/1).

    When ``record_tick`` is False, only episode/moment boundaries are updated — used
    before life tick so surprise episodes can attach active ids; call again with
    ``record_tick=True`` after affect to append the tick row.
    """
    set_hippo_mode(state, HIPPO_MODE_WAKE)
    idx = ensure_hippo_index(state)
    scene_id = str(scene_id or "").strip()
    if not scene_id:
        raise ValueError("hippo_wake_index_tick requires scene_id")

    boundaries: list[str] = []
    if idx.get("active_scene_id") and idx["active_scene_id"] != scene_id:
        close_episode_boundary(state, reason="scene_change")
        boundaries.append("scene_change")

    if idx.get("active_episode_id") is None:
        _open_episode(idx, scene_id=scene_id)
        boundaries.append("episode_opened")

    beat_key = str(beat_id).strip() if beat_id else None
    if beat_key and idx.get("active_beat_id") and idx["active_beat_id"] != beat_key:
        close_moment_boundary(state, reason="beat_change")
        boundaries.append("beat_change")

    if idx.get("active_moment_id") is None:
        _open_moment(idx, beat_id=beat_key, scene_id=scene_id)
        boundaries.append("moment_opened")

    moment_id = str(idx["active_moment_id"])
    episode_id = str(idx["active_episode_id"])
    if not record_tick:
        return {
            "moment_id": moment_id,
            "episode_id": episode_id,
            "scene_id": scene_id,
            "beat_id": beat_key,
            "boundaries": boundaries,
            "hippo_mode": HIPPO_MODE_WAKE,
            "record_tick": False,
        }

    buf = idx.setdefault("moment_buffer", {}).setdefault(
        moment_id,
        {"scene_id": scene_id, "beat_id": beat_key, "modalities": []},
    )
    tick_row: dict[str, Any] = {
        "seq": seq,
        "stream_id": stream_id,
        "visual_delta": visual_delta,
        "coactive": coactive,
    }
    if affect_snapshot:
        tick_row["affect"] = affect_snapshot
    if modality_tags:
        tick_row["modality_tags"] = list(modality_tags)
    buf.setdefault("ticks", []).append({k: v for k, v in tick_row.items() if v is not None})
    mods = buf.setdefault("modalities", [])
    for tag in modality_tags or []:
        if tag not in mods:
            mods.append(tag)
    if coactive and "av_coactive" not in mods:
        mods.append("av_coactive")

    _journal(
        idx,
        event="wake_tick",
        moment_id=moment_id,
        episode_id=episode_id,
        extra={
            "scene_id": scene_id,
            "beat_id": beat_key,
            "seq": seq,
            "coactive": coactive,
            "boundaries": boundaries,
        },
    )
    return {
        "moment_id": moment_id,
        "episode_id": episode_id,
        "scene_id": scene_id,
        "beat_id": beat_key,
        "boundaries": boundaries,
        "hippo_mode": HIPPO_MODE_WAKE,
    }
