#!/usr/bin/env python3
"""Validate paired / motion listen beats before ingest — gate, not smoke after the fact."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from casa.domain.listen_beat_model import (
    BEAT_KIND_MOTION,
    beat_kind,
    normalize_keyframes,
)


@dataclass
class BeatCheck:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    beats: list[dict[str, Any]] = field(default_factory=list)
    timeline: list[str] = field(default_factory=list)


def _chapter_duration(scene: dict[str, Any]) -> float:
    return max(0.0, float(scene.get("t1") or 0) - float(scene.get("t0") or 0))


def _accepted_beat_modes() -> frozenset[str]:
    return frozenset(
        {
            "scene_cut_paired",
            "human_curated",
            "human_curated_motion",
        }
    )


def validate_scene_beats(
    scene: dict[str, Any],
    bundle_dir: Path,
    *,
    require_paired: bool = True,
    max_gap_sec: float = 0.25,
    min_beat_sec: float = 0.5,
    max_beat_sec_paired: float = 8.0,
    max_beat_sec_motion: float = 20.0,
    min_beats: int = 2,
    min_motion_keyframes: int = 2,
    max_motion_keyframes: int = 12,
) -> BeatCheck:
    """Check beats[] + files + timeline continuity before listen_mass_ingest."""
    bundle_dir = bundle_dir.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    timeline: list[str] = []

    sid = str(scene.get("id") or "?")
    dur = _chapter_duration(scene)
    if dur <= 0:
        errors.append(f"{sid}: invalid chapter window t0/t1")
        return BeatCheck(ok=False, errors=errors)

    beats = scene.get("beats")
    if not isinstance(beats, list) or not beats:
        errors.append(f"{sid}: missing beats[] — run scene-cut reburst first")
        return BeatCheck(ok=False, errors=errors)

    if len(beats) < min_beats:
        errors.append(f"{sid}: only {len(beats)} beats (need >= {min_beats})")

    mode = str(scene.get("beat_mode") or "")
    if require_paired and mode not in _accepted_beat_modes():
        warnings.append(f"{sid}: beat_mode={mode!r} unexpected for ingest")

    prev_t1: float | None = None
    for i, beat in enumerate(beats):
        if not isinstance(beat, dict):
            errors.append(f"{sid}: beat[{i}] not an object")
            continue
        bid = str(beat.get("id") or f"b{i:03d}")
        kind = beat_kind(beat)
        try:
            bt0 = float(beat.get("t0"))
            bt1 = float(beat.get("t1"))
        except (TypeError, ValueError):
            errors.append(f"{sid}: beat {bid} missing numeric t0/t1")
            continue

        beat_dur = bt1 - bt0
        max_dur = max_beat_sec_motion if kind == BEAT_KIND_MOTION else max_beat_sec_paired
        if beat_dur < min_beat_sec:
            errors.append(f"{sid}: beat {bid} too short ({beat_dur:.2f}s)")
        if beat_dur > max_dur:
            errors.append(f"{sid}: beat {bid} too long ({beat_dur:.2f}s, max {max_dur})")
        if prev_t1 is not None and abs(bt0 - prev_t1) > max_gap_sec:
            errors.append(
                f"{sid}: gap between beats {i - 1} and {i}: {bt0 - prev_t1:.2f}s (max {max_gap_sec})"
            )
        prev_t1 = bt1

        if kind == BEAT_KIND_MOTION:
            keyframes = normalize_keyframes(beat)
            if len(keyframes) < min_motion_keyframes:
                errors.append(f"{sid}: beat {bid} motion needs >= {min_motion_keyframes} keyframes")
            if len(keyframes) > max_motion_keyframes:
                errors.append(f"{sid}: beat {bid} motion has {len(keyframes)} keyframes (max {max_motion_keyframes})")
            for ki, kf in enumerate(keyframes):
                ref = str(kf.get("path") or "").strip()
                if not ref:
                    errors.append(f"{sid}: beat {bid} keyframe[{ki}] missing path")
                    continue
                if not (bundle_dir / ref).is_file():
                    errors.append(f"{sid}: missing file {ref}")
                try:
                    ft_rel = float(kf["frame_t"])
                    if ft_rel < bt0 - 0.05 or ft_rel > bt1 + 0.05:
                        errors.append(
                            f"{sid}: beat {bid} keyframe[{ki}] frame_t {ft_rel:.2f}s outside [{bt0},{bt1}]"
                        )
                except (KeyError, TypeError, ValueError):
                    errors.append(f"{sid}: beat {bid} keyframe[{ki}] missing frame_t")
            kf_note = " ".join(
                f"@{float(k['frame_t']):.2f}s" for k in keyframes[:4] if "frame_t" in k
            )
            if len(keyframes) > 4:
                kf_note += " …"
            timeline.append(
                f"  {bid}  {bt0:7.2f}–{bt1:7.2f}s  ({beat_dur:5.2f}s) motion×{len(keyframes)} {kf_note}"
            )
        else:
            path_ref = str(beat.get("path") or "").strip()
            if not path_ref:
                errors.append(f"{sid}: beat {bid} missing path")
            elif not (bundle_dir / path_ref).is_file():
                errors.append(f"{sid}: missing file {path_ref}")
            ft_note = ""
            ft = beat.get("frame_t")
            if ft is not None:
                try:
                    ft_rel = float(ft)
                    if ft_rel < bt0 - 0.05 or ft_rel > bt1 + 0.05:
                        errors.append(f"{sid}: beat {bid} frame_t {ft_rel:.2f}s outside [{bt0},{bt1}]")
                    ft_note = f" frame@{ft_rel:.2f}s"
                except (TypeError, ValueError):
                    pass
            timeline.append(
                f"  {bid}  {bt0:7.2f}–{bt1:7.2f}s  ({beat_dur:5.2f}s){ft_note}  {path_ref}"
            )

    if beats:
        try:
            first_t0 = float(beats[0].get("t0"))
            last_t1 = float(beats[-1].get("t1"))
        except (TypeError, ValueError):
            first_t0 = -1
            last_t1 = -1
        if abs(first_t0) > max_gap_sec:
            errors.append(f"{sid}: first beat t0={first_t0} (expected ~0)")
        if abs(last_t1 - dur) > max(0.5, max_gap_sec):
            errors.append(f"{sid}: last beat t1={last_t1} vs chapter dur {dur:.2f}")

    ok = not errors
    return BeatCheck(ok=ok, errors=errors, warnings=warnings, beats=beats, timeline=timeline)


def format_beat_report(check: BeatCheck, *, scene_title: str = "") -> str:
    lines = ["LISTEN BEATS — pre-ingest gate"]
    if scene_title:
        lines.append(f"chapter: {scene_title}")
    if check.timeline:
        lines.append("timeline (audio windows + visual slots):")
        lines.extend(check.timeline)
    if check.warnings:
        lines.append("warnings:")
        lines.extend(f"  ! {w}" for w in check.warnings)
    if check.errors:
        lines.append("FAIL:")
        lines.extend(f"  - {e}" for e in check.errors)
    else:
        n_motion = sum(1 for b in check.beats if beat_kind(b) == BEAT_KIND_MOTION)
        n_paired = len(check.beats) - n_motion
        lines.append(
            f"PASS: {len(check.beats)} beats ({n_paired} paired, {n_motion} motion) ready for ingest"
        )
    return "\n".join(lines)
