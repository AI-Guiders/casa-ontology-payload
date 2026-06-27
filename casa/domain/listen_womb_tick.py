#!/usr/bin/env python3
"""Online listen stream — imprint + motion surprise per wall-clock step (womb tick v0)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from casa.prisms.auditory.imprint import imprint_auditory_window
from casa.prisms.memory.memory_prisms import ensure_prisms, run_sleep
from casa.prisms.memory.prism_spawn import spawn_content_lattice
from casa.prisms.memory.vocab import listen_scene_anchor
from casa.prisms.visual.imprint import imprint_visual_scene_frame
from casa.sensory.chapter_scene_cuts import extract_beat_frame
from casa.sensory.codecs.retinal_lrgb import encode_retinal_lrgb
from casa.sensory.load_rgb_frame import load_rgb_frame
from casa.sensory.rgb_frame import RgbFrame


def visual_token_fingerprint(frame: RgbFrame) -> frozenset[str]:
    """Quantized LRGB tokens for frame-to-frame delta (motion proxy)."""
    plan = encode_retinal_lrgb(frame, frame_id="_fp")
    tokens: set[str] = set()
    for placements in plan.placements_by_lattice.values():
        for p in placements:
            tokens.add(p.token)
    return frozenset(tokens)


def fingerprint_delta(prev: frozenset[str] | None, curr: frozenset[str]) -> float:
    """Jaccard distance in [0, 1]; 0 = identical imprint tokens."""
    if prev is None:
        return 1.0
    if not prev and not curr:
        return 0.0
    inter = len(prev & curr)
    union = len(prev | curr)
    return 1.0 - (inter / union) if union else 0.0


def sample_stream_times(
    t0: float,
    t1: float,
    *,
    interval_sec: float,
) -> list[float]:
    start = float(t0)
    end = float(t1)
    step = max(0.1, float(interval_sec))
    if end <= start:
        return []
    times: list[float] = []
    t = start
    while t <= end + 1e-6:
        times.append(round(t, 3))
        t += step
    return times


@dataclass
class WombTickRecord:
    seq: int
    t_rel: float
    frame_id: str
    window_id: str
    visual_delta: float
    visual_placements: dict[str, int]
    audio_duration_ms: int | None
    audio_placements: dict[str, int] | None
    field_version: int
    episode_id: str | None
    moment_id: str | None = None
    beat_id: str | None = None
    hippo_wake: dict[str, Any] | None = None
    life_tick: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        out = {
            "seq": self.seq,
            "t_rel": self.t_rel,
            "frame_id": self.frame_id,
            "window_id": self.window_id,
            "visual_delta": round(self.visual_delta, 4),
            "visual_placements": self.visual_placements,
            "audio_duration_ms": self.audio_duration_ms,
            "audio_placements": self.audio_placements,
            "field_version": self.field_version,
            "episode_id": self.episode_id,
            "moment_id": self.moment_id,
            "beat_id": self.beat_id,
        }
        if self.hippo_wake is not None:
            out["hippo_wake"] = self.hippo_wake
        if self.life_tick is not None:
            out["life_tick"] = self.life_tick
        return out


@dataclass
class WombStreamReport:
    scene_id: str
    stream_id: str
    interval_sec: float
    ticks: list[WombTickRecord] = field(default_factory=list)
    sleep: dict[str, Any] | None = None
    field_version: int = 0
    hippo_index: dict[str, Any] | None = None

    def summary(self) -> dict[str, Any]:
        deltas = [t.visual_delta for t in self.ticks]
        motion_ticks = sum(1 for d in deltas if d >= 0.08)
        life_ticks = [t.life_tick for t in self.ticks if t.life_tick]
        surprise_ticks = sum(1 for rep in life_ticks if rep.get("surprise"))
        out = {
            "scene_id": self.scene_id,
            "stream_id": self.stream_id,
            "tick_count": len(self.ticks),
            "interval_sec": self.interval_sec,
            "mean_visual_delta": round(sum(deltas) / len(deltas), 4) if deltas else 0.0,
            "max_visual_delta": round(max(deltas), 4) if deltas else 0.0,
            "motion_ticks_ge_0_08": motion_ticks,
            "life_tick_count": len(life_ticks),
            "life_surprise_ticks": surprise_ticks,
            "field_version": self.field_version,
            "sleep_ran": self.sleep is not None,
        }
        if self.hippo_index is not None:
            out["hippo_index"] = self.hippo_index
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "ticks": [t.to_dict() for t in self.ticks],
            "sleep": self.sleep,
            "hippo_index": self.hippo_index,
        }


def _ensure_listen_state(state: dict | None) -> dict:
    from casa.prisms.memory.memory_prisms import memory_lattices

    runtime = ensure_prisms(state or {"schema_version": "multi_prism_v1", "field_version": 0})
    lats = memory_lattices(runtime, "prism_memory")
    if "L3_phrase" not in lats:
        spawn_content_lattice(runtime, "prism_memory", "L3_phrase", z_level=3)
    if "L2_word" not in lats:
        spawn_content_lattice(runtime, "prism_memory", "L2_word", z_level=2)
    from casa.prisms.auditory.bootstrap import ensure_prism_auditory
    from casa.prisms.visual.bootstrap import ensure_prism_visual

    ensure_prism_visual(runtime)
    ensure_prism_auditory(runtime)
    return runtime


def _life_tick_summary(report: dict[str, Any]) -> dict[str, Any]:
    control = report.get("control") if isinstance(report.get("control"), dict) else {}
    surprise = control.get("surprise")
    return {
        "tick": report.get("tick"),
        "sn_mode": report.get("sn_mode"),
        "surprise": bool(surprise),
        "control_value": control.get("value"),
    }


def _modality_tags_for_stream_tick(*, audio_active: bool, visual_delta: float) -> list[str]:
    tags: list[str] = []
    if audio_active:
        tags.append("auditory")
    if visual_delta > 0.0:
        tags.append("visual")
    return tags


def _hippo_index_summary(state: dict) -> dict[str, Any]:
    from casa.prisms.hippo.wake_index import ensure_hippo_index

    idx = ensure_hippo_index(state)
    journal = idx.get("journal") or []
    events: dict[str, int] = {}
    for row in journal:
        if isinstance(row, dict):
            ev = str(row.get("event") or "")
            events[ev] = events.get(ev, 0) + 1
    return {
        "active_episode_id": idx.get("active_episode_id"),
        "active_moment_id": idx.get("active_moment_id"),
        "active_beat_id": idx.get("active_beat_id"),
        "moment_buffer_count": len(idx.get("moment_buffer") or {}),
        "journal_len": len(journal),
        "journal_events": events,
    }


def run_listen_womb_stream(
    state: dict,
    scene: dict[str, Any],
    *,
    video_path: Path,
    wav_path: Path | None,
    work_dir: Path,
    store_dir: Path | None = None,
    interval_sec: float = 0.5,
    t_start_rel: float | None = None,
    t_end_rel: float | None = None,
    run_sleep_at_end: bool = False,
    sleep_bundle: dict | None = None,
    runtime: Any | None = None,
    run_life_tick: bool = True,
) -> tuple[dict, WombStreamReport]:
    """Step through chapter video in real time slices; imprint A+V; optional macro life tick."""
    state = _ensure_listen_state(state)
    sid = str(scene.get("id") or "scene")
    caption = str(scene.get("caption") or scene.get("chapter_title") or "")
    chapter_t0 = float(scene.get("t0") or 0.0)
    chapter_t1 = float(scene.get("t1") or chapter_t0)
    stream_id = str(scene.get("stream_id") or sid)

    t0_rel = float(t_start_rel if t_start_rel is not None else chapter_t0)
    t1_rel = float(t_end_rel if t_end_rel is not None else chapter_t1)
    times = sample_stream_times(t0_rel, t1_rel, interval_sec=interval_sec)

    listen_scene_anchor(state, sid, caption, copies=2)

    work_dir = work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    report = WombStreamReport(
        scene_id=sid,
        stream_id=stream_id,
        interval_sec=interval_sec,
    )
    prev_fp: frozenset[str] | None = None
    bundle = sleep_bundle or {"claims": [], "graph": {"edges": []}}

    from casa.domain.listen_beat_lookup import resolve_beat_id_at_t_rel
    from casa.prisms.hippo.wake_index import close_moment_boundary, hippo_wake_index_tick

    for seq, t_rel in enumerate(times):
        t_abs = chapter_t0 + t_rel
        frame_path = work_dir / f"tick_{seq:04d}.jpg"
        if not extract_beat_frame(video_path, t_abs=t_abs, out_jpg=frame_path):
            continue
        frame = load_rgb_frame(frame_path)
        fp = visual_token_fingerprint(frame)
        vis_delta = fingerprint_delta(prev_fp, fp)
        prev_fp = fp

        frame_id = f"{stream_id}-f{seq:04d}"
        window_id = f"{stream_id}-tick{seq:04d}"
        t_window_start = max(t0_rel, t_rel - interval_sec)
        macro_tick = int(runtime.wm.tick) + 1 if runtime is not None and runtime.wm is not None else seq
        fv_before = int(state.get("field_version") or 0)

        visual = imprint_visual_scene_frame(
            state,
            frame,
            scene_id=sid,
            frame_id=frame_id,
            audio_window_id=window_id,
            record_episode=True,
        )

        audio: dict[str, Any] | None = None
        if wav_path is not None and wav_path.is_file():
            audio = imprint_auditory_window(
                state,
                wav_path,
                scene_id=sid,
                window_id=window_id,
                t0_sec=chapter_t0 + t_window_start,
                t1_sec=chapter_t0 + t_rel,
                speaker=str(scene.get("speaker") or "") or None,
                record_episode=True,
            )

        audio_placements = dict(audio.get("placements") or {}) if audio else {}
        audio_placements_n = sum(int(v) for v in audio_placements.values())
        audio_active = audio_placements_n > 0 or bool(audio and int(audio.get("duration_ms") or 0) > 0)

        from casa.prisms.perceptual import perceptual_prepare_life_sensory

        percept_rep = perceptual_prepare_life_sensory(
            state,
            stream_id=stream_id,
            seq=seq,
            t_rel=t_rel,
            visual_delta=vis_delta,
            audio_active=audio_active,
            audio_placements=audio_placements_n,
            aud_window_id=window_id,
            vis_frame_id=frame_id,
        )

        beat_id = resolve_beat_id_at_t_rel(scene, t_rel)
        modality_tags = _modality_tags_for_stream_tick(audio_active=audio_active, visual_delta=vis_delta)
        hippo_wake_index_tick(
            state,
            scene_id=sid,
            beat_id=beat_id,
            stream_id=stream_id,
            seq=seq,
            visual_delta=vis_delta,
            coactive=bool(percept_rep.get("coactive")),
            modality_tags=modality_tags,
            record_tick=False,
        )

        life_rep: dict[str, Any] | None = None
        tick_report: dict[str, Any] | None = None
        if runtime is not None and run_life_tick:
            from casa.prisms.memory.agent_life import run_life_tick as agent_run_life_tick

            tick_report = agent_run_life_tick(runtime, partner_turn=False, tick_log=True)
            state = runtime.state
            life_rep = _life_tick_summary(tick_report)
            life_rep["coactive"] = bool(percept_rep.get("coactive"))

        from casa.prisms.affect import affect_after_listen_tick

        affect_rep = affect_after_listen_tick(
            state,
            sid,
            tick=macro_tick,
            visual_delta=vis_delta,
            coactive=bool(percept_rep.get("coactive")),
            surprise=bool(life_rep and life_rep.get("surprise")),
        )

        hippo_rep = hippo_wake_index_tick(
            state,
            scene_id=sid,
            beat_id=beat_id,
            stream_id=stream_id,
            seq=seq,
            visual_delta=vis_delta,
            coactive=bool(percept_rep.get("coactive")),
            affect_snapshot={
                "core_axes": affect_rep.core.axes.to_dict(),
                "drivers": list(affect_rep.drivers),
            },
            modality_tags=modality_tags,
            record_tick=True,
        )

        impulse_row: dict[str, Any] | None = None
        if store_dir is not None:
            from casa.prisms.auditory.imprint import auditory_tokens_on_field
            from casa.prisms.visual.imprint import visual_tokens_on_field
            from casa.nervous.sensory_hooks import (
                ensure_impulse_macro_tick,
                record_affect_listen_impulse,
                record_listen_stream_step_impulse,
                record_percept_life_impulse,
                record_vision_gate_impulse,
            )

            ensure_impulse_macro_tick(tick_id=macro_tick, store_dir=store_dir)
            fv_after_imprint = int(state.get("field_version") or 0)
            impulse_row = {
                "listen": record_listen_stream_step_impulse(
                    store_dir=store_dir,
                    tick_id=macro_tick,
                    scene_id=sid,
                    stream_id=stream_id,
                    seq=seq,
                    t_rel=t_rel,
                    field_version_before=fv_before,
                    field_version_after=fv_after_imprint,
                    visual=visual,
                    visual_tokens=visual_tokens_on_field(state, sid),
                    auditory=audio,
                    auditory_tokens=auditory_tokens_on_field(state, sid) if audio else [],
                    visual_delta=vis_delta,
                ),
                "vision": record_vision_gate_impulse(
                    store_dir=store_dir,
                    tick_id=macro_tick,
                    frame_id=frame_id,
                    visual_delta=vis_delta,
                    coactive=bool(percept_rep.get("coactive")),
                ),
                "percept": record_percept_life_impulse(
                    store_dir=store_dir,
                    tick_id=macro_tick,
                    percept_rep=percept_rep if isinstance(percept_rep, dict) else None,
                ),
                "affect": record_affect_listen_impulse(
                    store_dir=store_dir,
                    tick_id=macro_tick,
                    scene_id=sid,
                    core_axes=affect_rep.core.axes.to_dict(),
                    drivers=affect_rep.drivers,
                ),
            }

        if life_rep is not None:
            life_rep["affect_drivers"] = list(affect_rep.drivers)
            if impulse_row is not None:
                merged = {**impulse_row}
                if tick_report is not None:
                    merged["orchestrator"] = tick_report.get("impulse")
                life_rep["impulse"] = merged

        report.ticks.append(
            WombTickRecord(
                seq=seq,
                t_rel=t_rel,
                frame_id=frame_id,
                window_id=window_id,
                visual_delta=vis_delta,
                visual_placements=dict(visual.get("placements") or {}),
                audio_duration_ms=int(audio.get("duration_ms") or 0) if audio else None,
                audio_placements=audio_placements or None,
                field_version=int(state.get("field_version") or 0),
                episode_id=str(hippo_rep.get("episode_id") or "") or None,
                moment_id=str(hippo_rep.get("moment_id") or "") or None,
                beat_id=beat_id,
                hippo_wake=hippo_rep,
                life_tick=life_rep,
            )
        )

    if report.ticks:
        close_moment_boundary(state, reason="stream_end")

    if run_sleep_at_end and report.ticks:
        report.sleep = run_sleep(state, bundle=bundle)
        if store_dir is not None and report.sleep:
            from casa.nervous.sensory_hooks import record_sleep_boundary_impulse

            last_tick = int(runtime.wm.tick) if runtime is not None and runtime.wm is not None else len(report.ticks)
            record_sleep_boundary_impulse(
                store_dir=store_dir,
                tick_id=last_tick,
                sleep_rep=report.sleep if isinstance(report.sleep, dict) else None,
            )

    report.field_version = int(state.get("field_version") or 0)
    report.hippo_index = _hippo_index_summary(state)
    return state, report


def write_womb_report(path: Path, report: WombStreamReport) -> None:
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
