"""Sensory / listen-stream impulse hooks (ADR-0080 + listen wire-gap)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.nervous.channels import ImpulseChannel, ImpulseOutcome
from casa.nervous.impulse import impulse_recorder


def ensure_impulse_macro_tick(*, tick_id: int, store_dir: Path) -> None:
    """Align stream imprint + life tick on one macro_tick id (idempotent)."""
    rec = impulse_recorder()
    if not rec.is_active:
        return
    rec.begin_tick(int(tick_id), store_dir.resolve())


def record_listen_stream_step_impulse(
    *,
    store_dir: Path,
    tick_id: int,
    scene_id: str,
    stream_id: str,
    seq: int,
    t_rel: float,
    field_version_before: int,
    field_version_after: int,
    visual: dict[str, Any] | None,
    visual_tokens: list[str] | None,
    auditory: dict[str, Any] | None,
    auditory_tokens: list[str] | None,
    visual_delta: float,
) -> dict[str, Any] | None:
    """One stream step: A+V imprint (online path, mirrors listen_moment)."""
    rec = impulse_recorder()
    if not rec.is_active:
        return None
    ensure_impulse_macro_tick(tick_id=tick_id, store_dir=store_dir)
    zones = ["linguistic"]
    motion = float(visual_delta) >= 0.08
    outcome = ImpulseOutcome.SILENT
    with rec.channel(ImpulseChannel.LISTEN_IMPRINT, store_dir=store_dir) as imp:
        imp.select(
            "stream_step",
            zone="linguistic",
            selected=[stream_id, f"seq:{seq}"],
            inputs={
                "tick_id": tick_id,
                "scene_id": scene_id,
                "stream_id": stream_id,
                "seq": seq,
                "t_rel": t_rel,
                "visual_delta": round(float(visual_delta), 4),
                "motion": motion,
                "field_version_before": field_version_before,
                "field_version_after": field_version_after,
            },
        )
        if auditory:
            zones.append("auditory")
            dyn = [t for t in (auditory_tokens or []) if str(t).startswith("A:dyn:")]
            imp.select(
                "auditory_imprint",
                zone="auditory",
                selected=dyn or ["imprinted"],
                inputs={
                    "scene_id": scene_id,
                    "window_id": auditory.get("window_id"),
                    "codec_id": auditory.get("codec_id"),
                    "duration_ms": auditory.get("duration_ms"),
                    "placements": auditory.get("placements"),
                },
            )
        if visual:
            zones.append("visual")
            frame_id = str(visual.get("frame_id") or "")
            imp.select(
                "visual_imprint",
                zone="visual",
                selected=[frame_id] if frame_id else ["imprinted"],
                inputs={
                    "scene_id": scene_id,
                    "frame_id": frame_id,
                    "codec_id": visual.get("codec_id"),
                    "placements": visual.get("placements"),
                },
            )
            if motion:
                outcome = ImpulseOutcome.FRAME_SELECTED
        summary = imp.finish(outcome, zones_touched=zones)
        return dict(summary)
    return None


def record_vision_gate_impulse(
    *,
    store_dir: Path,
    tick_id: int,
    frame_id: str,
    visual_delta: float,
    coactive: bool = False,
) -> dict[str, Any] | None:
    rec = impulse_recorder()
    if not rec.is_active:
        return None
    ensure_impulse_macro_tick(tick_id=tick_id, store_dir=store_dir)
    motion = float(visual_delta) >= 0.08
    with rec.channel(ImpulseChannel.VISION_GATE, store_dir=store_dir) as imp:
        imp.route(
            "retinal_gate",
            zone="spatial",
            selected=["percept.vis.motion"] if motion else ["percept.vis.still"],
            inputs={
                "tick_id": tick_id,
                "frame_id": frame_id,
                "visual_delta": round(float(visual_delta), 4),
                "coactive": coactive,
            },
        )
        outcome = ImpulseOutcome.FRAME_SELECTED if motion else ImpulseOutcome.HOLD
        summary = imp.finish(outcome, zones_touched=["spatial", "executive"])
        return dict(summary)
    return None


def record_percept_life_impulse(
    *,
    store_dir: Path,
    tick_id: int,
    percept_rep: dict[str, Any] | None,
) -> dict[str, Any] | None:
    rec = impulse_recorder()
    if not rec.is_active:
        return None
    if not isinstance(percept_rep, dict) or not percept_rep:
        return None
    ensure_impulse_macro_tick(tick_id=tick_id, store_dir=store_dir)
    tokens = list(percept_rep.get("tokens") or [])[:12]
    modalities = list(percept_rep.get("modalities") or [])
    coactive = bool(percept_rep.get("coactive"))
    zones = ["executive"]
    if "visual_stream" in modalities:
        zones.append("spatial")
    if "listen_stream" in modalities:
        zones.append("auditory")
    if "text_stream" in modalities:
        zones.append("linguistic")
    with rec.channel(ImpulseChannel.PERCEPT_LIFE, store_dir=store_dir) as imp:
        imp.select(
            "thalamic_gate",
            zone="executive",
            selected=tokens[:6] or ["percept.life.tick"],
            inputs={
                "tick_id": tick_id,
                "modalities": modalities,
                "coactive": coactive,
                "aud_window_id": percept_rep.get("aud_window_id"),
                "vis_frame_id": percept_rep.get("vis_frame_id"),
            },
        )
        outcome = ImpulseOutcome.FRAME_SELECTED if coactive else ImpulseOutcome.NO_OP
        summary = imp.finish(outcome, zones_touched=list(dict.fromkeys(zones)))
        return dict(summary)
    return None


def record_affect_listen_impulse(
    *,
    store_dir: Path,
    tick_id: int,
    scene_id: str,
    theme_cluster: str,
    core_axes: dict[str, Any] | None,
) -> dict[str, Any] | None:
    rec = impulse_recorder()
    if not rec.is_active:
        return None
    ensure_impulse_macro_tick(tick_id=tick_id, store_dir=store_dir)
    with rec.channel(ImpulseChannel.AFFECT_LISTEN, store_dir=store_dir) as imp:
        imp.activate(
            "listen_theme",
            zone="emotional",
            inputs={
                "tick_id": tick_id,
                "scene_id": scene_id,
                "theme_cluster": theme_cluster,
                "axes": dict(core_axes or {}),
            },
        )
        summary = imp.finish(ImpulseOutcome.NO_OP, zones_touched=["emotional"])
        return dict(summary)
    return None


def record_av_coactive_bind_impulse(
    *,
    store_dir: Path,
    tick_id: int,
    bind_rep: dict[str, Any] | None,
) -> dict[str, Any] | None:
    rec = impulse_recorder()
    if not rec.is_active:
        return None
    if not isinstance(bind_rep, dict):
        return None
    ensure_impulse_macro_tick(tick_id=tick_id, store_dir=store_dir)
    bound = bool(bind_rep.get("bound"))
    already = bool(bind_rep.get("already"))
    with rec.channel(ImpulseChannel.AV_COACTIVE, store_dir=store_dir) as imp:
        imp.select(
            "av_coactive_bind",
            zone="memory",
            selected=[
                str(bind_rep.get("aud_concept_id") or ""),
                str(bind_rep.get("vis_concept_id") or ""),
            ],
            inputs={
                "tick_id": tick_id,
                "bound": bound,
                "already": already,
                "provenance": (bind_rep.get("extract") or {}).get("provenance"),
            },
        )
        outcome = ImpulseOutcome.COMPOSED if bound else ImpulseOutcome.NO_OP
        if already:
            outcome = ImpulseOutcome.HOLD
        summary = imp.finish(outcome, zones_touched=["auditory", "spatial", "memory"])
        return dict(summary)
    return None


def record_motor_heard_bind_impulse(
    *,
    store_dir: Path,
    tick_id: int,
    bind_rep: dict[str, Any] | None,
) -> dict[str, Any] | None:
    rec = impulse_recorder()
    if not rec.is_active or not isinstance(bind_rep, dict):
        return None
    ensure_impulse_macro_tick(tick_id=tick_id, store_dir=store_dir)
    bound = bool(bind_rep.get("bound"))
    with rec.channel(ImpulseChannel.MOTOR_SPEECH, store_dir=store_dir) as imp:
        imp.select(
            "motor_heard_bind",
            zone="motor",
            selected=[
                str(bind_rep.get("motor_concept_id") or ""),
                str(bind_rep.get("aud_concept_id") or ""),
            ],
            inputs={"tick_id": tick_id, "bound": bound, "already": bool(bind_rep.get("already"))},
        )
        outcome = ImpulseOutcome.COMPOSED if bound else ImpulseOutcome.NO_OP
        summary = imp.finish(outcome, zones_touched=["motor", "auditory"])
        return dict(summary)
    return None


def record_sleep_boundary_impulse(
    *,
    store_dir: Path,
    tick_id: int,
    sleep_rep: dict[str, Any] | None,
) -> dict[str, Any] | None:
    rec = impulse_recorder()
    if not rec.is_active or not sleep_rep:
        return None
    ensure_impulse_macro_tick(tick_id=tick_id, store_dir=store_dir)
    with rec.channel(ImpulseChannel.SLEEP_TRAIN, store_dir=store_dir) as imp:
        imp.route(
            "sleep_boundary",
            zone="memory",
            inputs={
                "tick_id": tick_id,
                "batch_size": sleep_rep.get("batch_size"),
                "extract_count": len(sleep_rep.get("extract") or []),
            },
        )
        summary = imp.finish(ImpulseOutcome.QUEUED, zones_touched=["memory"])
        return dict(summary)
    return None
