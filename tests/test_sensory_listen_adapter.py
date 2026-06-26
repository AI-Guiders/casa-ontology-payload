#!/usr/bin/env python3
"""Listen sensory adapter — ADR-0027 file_replay layer."""

from __future__ import annotations

from pathlib import Path

from casa.sensory.adapters.listen_corpus import (
    capture_listen_scene,
    resolve_scene_frames,
    resolve_scene_wav,
)


def test_resolve_scene_wav_relative_to_manifest(tmp_path: Path) -> None:
    wav = tmp_path / "audio" / "clip.wav"
    wav.parent.mkdir(parents=True)
    wav.write_bytes(b"RIFF")
    scene = {"id": "s1", "wav": "audio/clip.wav"}
    got = resolve_scene_wav(None, scene, manifest_dir=tmp_path)
    assert got == wav


def test_capture_listen_scene_frame_only(tmp_path: Path) -> None:
    frame = tmp_path / "f.jpg"
    frame.write_bytes(b"\xff\xd8\xff")
    scene = {"id": "s2", "frame": "f.jpg"}
    cap = capture_listen_scene(scene, manifest_dir=tmp_path)
    assert cap.backend_id == "file_replay"
    assert cap.scene_id == "s2"
    assert cap.wav_path is None
    assert len(cap.frame_entries) == 1
    assert cap.frame_entries[0][0] == frame


def test_capture_listen_scene_resolves_wav(tmp_path: Path) -> None:
    wav = tmp_path / "s.wav"
    wav.write_bytes(b"RIFF")
    scene = {"id": "s3", "wav": "s.wav"}
    cap = capture_listen_scene(scene, manifest_dir=tmp_path)
    assert cap.wav_path == wav
