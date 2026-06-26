#!/usr/bin/env python3
"""Multimodal listen moment — visual + auditory on shared scene_id."""

from __future__ import annotations

from pathlib import Path

from casa.domain.visual_tract import LATTICE_V1_LUM
from casa.domain.prism_ids import PRISM_VISUAL
from casa.domain.prism_wire import prism_block
from casa.prisms.memory.listen_moment import listen_moment
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.prism_spawn import spawn_content_lattice
from casa.prisms.visual.imprint import scene_visual_token
from casa.sensory.load_wav import write_synthetic_contour_wav
from casa.sensory.sample_ppm import write_synthetic_room_ppm


def _minimal_state() -> dict:
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    spawn_content_lattice(state, "prism_memory", "L3_phrase", z_level=3)
    spawn_content_lattice(state, "prism_memory", "L2_word", z_level=2)
    return state


def test_listen_moment_visual_and_audio_same_scene(tmp_path: Path) -> None:
    frame = tmp_path / "masha_frame.ppm"
    wav = tmp_path / "masha_line.wav"
    write_synthetic_room_ppm(frame, width=64, height=48)
    write_synthetic_contour_wav(wav, stereo=True, pan=-0.2)

    state = _minimal_state()
    moment = listen_moment(
        state,
        {
            "id": "masha-moment-001",
            "speaker": "masha",
        },
        wav_path=wav,
        frame_path=frame,
    )

    assert moment["recalled_words"] == []

    assert moment["audio"] is not None
    assert moment["visual"] is not None
    assert scene_visual_token("masha-moment-001") in moment["visual_tokens"]
    assert any(t.startswith("A:energy:") for t in moment["auditory_tokens"])

    vis_block = prism_block(state, PRISM_VISUAL)
    lum = (vis_block.get("lattices") or {}).get(LATTICE_V1_LUM) or {}
    flat = [tok for cell in (lum.get("cells") or []) for tok in cell]
    assert scene_visual_token("masha-moment-001") in flat
    assert any(tok.startswith("V:") for tok in flat)


def test_vocalization_visual_only_no_words(tmp_path: Path) -> None:
    frame = tmp_path / "medved.ppm"
    wav = tmp_path / "medved.wav"
    write_synthetic_room_ppm(frame, width=48, height=36)
    write_synthetic_contour_wav(wav, stereo=True, base_freq=95.0)

    state = _minimal_state()
    moment = listen_moment(
        state,
        {"id": "medved-grunt-vis", "speaker": "medved"},
        wav_path=wav,
        frame_path=frame,
    )

    assert moment["recalled_words"] == []
    assert moment["visual"] is not None
    assert moment["visual_frame_count"] == 1
    assert scene_visual_token("medved-grunt-vis") in moment["visual_tokens"]


def test_listen_moment_multi_frame_burst(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    frames_dir = bundle / "frames" / "00-scene"
    frames_dir.mkdir(parents=True)
    wav = bundle / "line.wav"
    f0 = frames_dir / "f0000.ppm"
    f1 = frames_dir / "f0001.ppm"
    write_synthetic_room_ppm(f0, width=40, height=30)
    write_synthetic_room_ppm(f1, width=44, height=32)
    write_synthetic_contour_wav(wav, stereo=True, pan=0.1)

    state = _minimal_state()
    moment = listen_moment(
        state,
        {
            "id": "burst-scene-001",
            "speaker": "narrator",
            "frames": [
                {"id": "v000", "t": 0.0, "path": "frames/00-scene/f0000.ppm"},
                {"id": "v001", "t": 12.0, "path": "frames/00-scene/f0001.ppm"},
            ],
        },
        wav_path=wav,
        manifest_dir=bundle,
    )

    assert moment["visual_frame_count"] == 2
    assert len(moment["visual_frames"]) == 2
    assert moment["visual_frames"][0]["frame_id"].endswith("-v000")
    assert moment["visual_frames"][1]["frame_id"].endswith("-v001")
    assert scene_visual_token("burst-scene-001") in moment["visual_tokens"]


def test_listen_moment_paired_beats(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    frames_dir = bundle / "frames" / "00-scene"
    frames_dir.mkdir(parents=True)
    wav = bundle / "line.wav"
    b0 = frames_dir / "b000.ppm"
    b1 = frames_dir / "b001.ppm"
    write_synthetic_room_ppm(b0, width=40, height=30)
    write_synthetic_room_ppm(b1, width=44, height=32)
    write_synthetic_contour_wav(wav, duration_sec=2.0, stereo=True)

    state = _minimal_state()
    moment = listen_moment(
        state,
        {
            "id": "paired-scene-001",
            "t0": 0.0,
            "t1": 2.0,
            "speaker": "narrator",
            "beat_mode": "scene_cut_paired",
            "beats": [
                {"id": "b000", "t0": 0.0, "t1": 1.0, "path": "frames/00-scene/b000.ppm"},
                {"id": "b001", "t0": 1.0, "t1": 2.0, "path": "frames/00-scene/b001.ppm"},
            ],
        },
        wav_path=wav,
        manifest_dir=bundle,
    )

    assert moment["paired_beats"] is True
    assert moment["visual_frame_count"] == 2
    assert len(moment["audio_beats"]) == 2
    assert moment["audio_beats"][0]["window_id"] == "paired-scene-001-b000"
    assert moment["visual_frames"][1]["frame_id"] == "paired-scene-001-b001"


def test_listen_moment_motion_beat(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    frames_dir = bundle / "frames" / "00-scene"
    frames_dir.mkdir(parents=True)
    wav = bundle / "line.wav"
    k0 = frames_dir / "b000-k0.ppm"
    k1 = frames_dir / "b000-k1.ppm"
    write_synthetic_room_ppm(k0, width=40, height=30)
    write_synthetic_room_ppm(k1, width=42, height=31)
    write_synthetic_contour_wav(wav, duration_sec=3.0, stereo=True)

    state = _minimal_state()
    moment = listen_moment(
        state,
        {
            "id": "motion-scene-001",
            "t0": 0.0,
            "t1": 3.0,
            "speaker": "narrator",
            "beat_mode": "human_curated_motion",
            "beats": [
                {
                    "id": "b000",
                    "kind": "motion",
                    "t0": 0.0,
                    "t1": 3.0,
                    "keyframes": [
                        {"frame_t": 0.5, "path": "frames/00-scene/b000-k0.ppm"},
                        {"frame_t": 2.0, "path": "frames/00-scene/b000-k1.ppm"},
                    ],
                },
            ],
        },
        wav_path=wav,
        manifest_dir=bundle,
    )

    assert moment["motion_beats"] == 1
    assert moment["visual_frame_count"] == 2
    assert len(moment["audio_beats"]) == 1
    assert moment["audio_beats"][0]["window_id"] == "motion-scene-001-b000"
    assert moment["visual_frames"][0]["frame_id"] == "motion-scene-001-b000-k0"
    assert moment["visual_frames"][1]["frame_id"] == "motion-scene-001-b000-k1"
