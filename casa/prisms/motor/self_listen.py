#!/usr/bin/env python3
"""Self-listen imprint from motor plan stub peripheral (ADR-0082)."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import Any

from casa.domain.auditory_tract import LATTICE_AUDIO_SPECTRUM
from casa.domain.motor_speech_plan import (
    MotorSpeechPlan,
    motor_plan_concept_id,
    motor_unit_concept_id,
    self_listen_aud_concept_id,
)
from casa.prisms.auditory.imprint import imprint_auditory_window
from casa.prisms.memory.memory_prisms import append_episode
from casa.sensory.load_wav import write_synthetic_contour_wav


def _base_freq_from_units(units: tuple[str, ...]) -> float:
    digest = hashlib.sha256("|".join(units).encode()).hexdigest()
    slot = int(digest[:4], 16) % 900
    return 120.0 + float(slot)


def _duration_from_units(units: tuple[str, ...]) -> float:
    return min(0.9, 0.18 + 0.08 * max(1, len(units)))


def synthesize_stub_wav(plan: MotorSpeechPlan, wav_path: Path) -> dict[str, Any]:
    """L4 stub: units → simple synth wav (outside field learning oracle)."""
    freq = _base_freq_from_units(plan.units)
    duration = _duration_from_units(plan.units)
    wav = write_synthetic_contour_wav(
        wav_path,
        duration_sec=duration,
        base_freq=freq,
        stereo=False,
    )
    return {
        "codec": "stub_sine_v1",
        "base_freq": freq,
        "duration_sec": duration,
        "duration_ms": wav.duration_ms,
    }


def record_motor_plan_episode(state: dict, plan: MotorSpeechPlan) -> dict[str, Any] | None:
    aud_cid = self_listen_aud_concept_id(plan.plan_id)
    motor_cid = motor_plan_concept_id(plan.plan_id)
    links: list[dict[str, Any]] = [
        {"src": motor_cid, "relation": "intended", "dst": aud_cid},
        {"src": motor_cid, "relation": "co_occurs", "dst": aud_cid},
    ]
    for unit in plan.units:
        links.append(
            {
                "src": motor_cid,
                "relation": "unit_of",
                "dst": motor_unit_concept_id(unit),
            }
        )
    ep = append_episode(
        state,
        cue=f"motor:{plan.plan_id}",
        surface_attempt="|".join(plan.units),
        correct=plan.plan_id,
        lattice_id=LATTICE_AUDIO_SPECTRUM,
        concept_id=motor_cid,
        scene=plan.scene_id,
        links=links,
        episode_source="wake",
    )
    return ep


def self_listen_from_plan(
    state: dict,
    plan: MotorSpeechPlan,
    *,
    store_dir: Path | None = None,
    wav_dir: Path | None = None,
) -> dict[str, Any]:
    """Execute stub peripheral + auditory self-imprint for motor plan."""
    tmp_root = wav_dir
    cleanup = False
    if tmp_root is None:
        tmp_root = Path(tempfile.mkdtemp(prefix="casa-motor-self-"))
        cleanup = True
    tmp_root.mkdir(parents=True, exist_ok=True)
    wav_path = tmp_root / f"{plan.self_listen_window_id}.wav"
    synth = synthesize_stub_wav(plan, wav_path)
    audio = imprint_auditory_window(
        state,
        wav_path,
        scene_id=plan.scene_id,
        window_id=plan.self_listen_window_id,
        speaker="self",
        record_episode=False,
    )
    motor_ep = record_motor_plan_episode(state, plan)
    heard_cid = self_listen_aud_concept_id(plan.plan_id)
    if motor_ep:
        append_episode(
            state,
            cue=f"heard_self:{plan.plan_id}",
            surface_attempt=heard_cid,
            correct=str(audio.get("audio_hash") or "")[:48],
            lattice_id=LATTICE_AUDIO_SPECTRUM,
            concept_id=heard_cid,
            scene=plan.scene_id,
            links=[
                {"src": heard_cid, "relation": "heard_self", "dst": motor_plan_concept_id(plan.plan_id)},
                {"src": motor_plan_concept_id(plan.plan_id), "relation": "co_occurs", "dst": heard_cid},
            ],
            episode_source="wake",
        )
    if cleanup:
        try:
            wav_path.unlink(missing_ok=True)
            tmp_root.rmdir()
        except OSError:
            pass
    _ = store_dir
    return {
        "plan": plan.to_dict(),
        "synth": synth,
        "self_listen": audio,
        "motor_episode_id": motor_ep.get("id") if motor_ep else None,
        "aud_concept_id": heard_cid,
        "motor_concept_id": motor_plan_concept_id(plan.plan_id),
    }
