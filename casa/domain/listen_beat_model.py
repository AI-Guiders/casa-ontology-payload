"""Listen beat kinds: paired (1 frame) vs motion (N keyframes, 1 audio window)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.sensory.adapters.media_path import resolve_media_path

BEAT_KIND_PAIRED = "paired"
BEAT_KIND_MOTION = "motion"


def beat_kind(beat: dict[str, Any]) -> str:
    explicit = str(beat.get("kind") or "").strip().lower()
    if explicit in (BEAT_KIND_PAIRED, BEAT_KIND_MOTION):
        return explicit
    keyframes = beat.get("keyframes")
    if isinstance(keyframes, list) and len(keyframes) >= 2:
        return BEAT_KIND_MOTION
    return BEAT_KIND_PAIRED


def normalize_keyframes(beat: dict[str, Any]) -> list[dict[str, Any]]:
    """Return keyframe rows with frame_t; for paired synthesize one from frame_t/path."""
    raw = beat.get("keyframes")
    if isinstance(raw, list) and raw:
        rows: list[dict[str, Any]] = []
        for item in raw:
            if isinstance(item, dict):
                row = dict(item)
            elif isinstance(item, (int, float)):
                row = {"frame_t": float(item)}
            else:
                continue
            if "frame_t" not in row:
                continue
            rows.append(row)
        if rows:
            return rows
    ft = beat.get("frame_t")
    path = str(beat.get("path") or "").strip()
    if ft is not None or path:
        row: dict[str, Any] = {}
        if ft is not None:
            row["frame_t"] = float(ft)
        if path:
            row["path"] = path
        if "frame_t" in row:
            return [row]
    return []


def assign_beat_media_paths(
    beat: dict[str, Any],
    *,
    chapter_dir: str,
    beat_id: str,
) -> dict[str, Any]:
    row = dict(beat)
    bid = str(beat_id)
    row["id"] = bid
    kind = beat_kind(row)
    row["kind"] = kind
    if kind == BEAT_KIND_MOTION:
        keyframes = normalize_keyframes(row)
        assigned: list[dict[str, Any]] = []
        for i, kf in enumerate(keyframes):
            item = dict(kf)
            item["path"] = str(item.get("path") or f"{chapter_dir}/{bid}-k{i}.jpg")
            assigned.append(item)
        row["keyframes"] = assigned
        row["path"] = assigned[0]["path"]
        if "frame_t" not in row and assigned:
            row["frame_t"] = assigned[0]["frame_t"]
    else:
        row["path"] = str(row.get("path") or f"{chapter_dir}/{bid}.jpg")
        row.pop("keyframes", None)
    return row


def count_expected_frame_files(beat: dict[str, Any]) -> int:
    kind = beat_kind(beat)
    if kind == BEAT_KIND_MOTION:
        return len(normalize_keyframes(beat))
    return 1 if str(beat.get("path") or "").strip() else 0


def resolve_beat_visuals(
    beat: dict[str, Any],
    bases: tuple[Path | None, ...],
) -> list[tuple[Path, str]]:
    """(image path, frame_id suffix) — one audio window may map to many visuals."""
    bid = str(beat.get("id") or "b000")
    kind = beat_kind(beat)
    if kind == BEAT_KIND_MOTION:
        out: list[tuple[Path, str]] = []
        for i, kf in enumerate(normalize_keyframes(beat)):
            ref = str(kf.get("path") or "").strip()
            if not ref:
                continue
            path = resolve_media_path(ref, bases)
            if path is not None:
                out.append((path, f"{bid}-k{i}"))
        return out
    ref = str(beat.get("path") or "").strip()
    if not ref:
        return []
    path = resolve_media_path(ref, bases)
    return [(path, bid)] if path is not None else []


def resolve_scene_beat_timeline(
    scene: dict[str, Any],
    bases: tuple[Path | None, ...],
) -> list[dict[str, Any]]:
    """Per-beat ingest plan: audio t0/t1 + visual slots."""
    beats = scene.get("beats")
    if not isinstance(beats, list):
        return []
    plans: list[dict[str, Any]] = []
    for i, item in enumerate(beats):
        if not isinstance(item, dict):
            continue
        bid = str(item.get("id") or f"b{i:03d}")
        try:
            bt0 = float(item["t0"])
            bt1 = float(item["t1"])
        except (KeyError, TypeError, ValueError):
            continue
        visuals = resolve_beat_visuals(item, bases)
        if not visuals:
            continue
        plans.append(
            {
                "beat_id": bid,
                "kind": beat_kind(item),
                "t0": bt0,
                "t1": bt1,
                "visuals": visuals,
            }
        )
    return plans
