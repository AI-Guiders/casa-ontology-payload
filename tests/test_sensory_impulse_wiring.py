#!/usr/bin/env python3
"""Impulse wiring for listen stream + orchestrator (ADR-0080)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from casa.nervous.channels import ImpulseChannel
from casa.nervous.sensory_hooks import (
    record_affect_listen_impulse,
    record_av_coactive_bind_impulse,
    record_listen_stream_step_impulse,
    record_percept_life_impulse,
    record_vision_gate_impulse,
)
from casa.prisms.auditory.imprint import imprint_auditory_window
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.sensory.load_wav import write_synthetic_contour_wav


@pytest.fixture(autouse=True)
def impulse_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CASA_IMPULSE_TRACE", "summary")


def test_sensory_impulse_hooks_write_trace() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = Path(tmp)
        state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
        wav = store / "a.wav"
        write_synthetic_contour_wav(wav)
        fv0 = int(state.get("field_version") or 0)
        audio = imprint_auditory_window(state, wav, scene_id="s1", window_id="s1-w0")
        fv1 = int(state.get("field_version") or 0)
        tick = 7

        record_listen_stream_step_impulse(
            store_dir=store,
            tick_id=tick,
            scene_id="s1",
            stream_id="s1",
            seq=0,
            t_rel=0.0,
            field_version_before=fv0,
            field_version_after=fv1,
            visual={"frame_id": "s1-f0000", "codec_id": "retinal_lrgb", "placements": {"V1_lum": 3}},
            visual_tokens=["V:scene:s1"],
            auditory=audio,
            auditory_tokens=["A:dyn:rise"],
            visual_delta=0.3,
        )
        record_vision_gate_impulse(
            store_dir=store,
            tick_id=tick,
            frame_id="s1-f0000",
            visual_delta=0.3,
            coactive=True,
        )
        record_percept_life_impulse(
            store_dir=store,
            tick_id=tick,
            percept_rep={
                "tokens": ["percept.av.coactive"],
                "modalities": ["visual_stream", "listen_stream"],
                "coactive": True,
                "aud_window_id": "s1-w0",
                "vis_frame_id": "s1-f0000",
            },
        )
        record_affect_listen_impulse(
            store_dir=store,
            tick_id=tick,
            scene_id="s1",
            theme_cluster="emotions",
            core_axes={"arousal": 0.08},
        )
        record_av_coactive_bind_impulse(
            store_dir=store,
            tick_id=tick,
            bind_rep={
                "bound": True,
                "aud_concept_id": "aud.window.s1-w0",
                "vis_concept_id": "vis.lum.frame.s1-f0000",
                "extract": {"provenance": "life_tick_coactive"},
            },
        )

        trace_path = store / "nervous" / "impulse_trace.jsonl"
        assert trace_path.is_file()
        channels = {
            json.loads(line).get("channel")
            for line in trace_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        assert channels >= {
            ImpulseChannel.LISTEN_IMPRINT.value,
            ImpulseChannel.VISION_GATE.value,
            ImpulseChannel.PERCEPT_LIFE.value,
            ImpulseChannel.AFFECT_LISTEN.value,
            ImpulseChannel.AV_COACTIVE.value,
        }
