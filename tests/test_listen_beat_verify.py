#!/usr/bin/env python3
"""Tests for listen beat pre-ingest validation."""

from __future__ import annotations

from pathlib import Path

from casa.domain.listen_beat_verify import validate_scene_beats


def test_validate_paired_beats_ok(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    frames = bundle / "frames" / "00-x"
    frames.mkdir(parents=True)
    (frames / "b000.jpg").write_bytes(b"jpeg")
    (frames / "b001.jpg").write_bytes(b"jpeg")
    scene = {
        "id": "scene-0",
        "t0": 0.0,
        "t1": 8.0,
        "beat_mode": "scene_cut_paired",
        "beats": [
            {"id": "b000", "t0": 0.0, "t1": 4.0, "path": "frames/00-x/b000.jpg", "frame_t": 2.0},
            {"id": "b001", "t0": 4.0, "t1": 8.0, "path": "frames/00-x/b001.jpg", "frame_t": 6.0},
        ],
    }
    check = validate_scene_beats(scene, bundle)
    assert check.ok
    assert len(check.beats) == 2


def test_validate_beats_missing_file(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    scene = {
        "id": "scene-0",
        "t0": 0.0,
        "t1": 10.0,
        "beat_mode": "scene_cut_paired",
        "beats": [{"id": "b000", "t0": 0.0, "t1": 10.0, "path": "frames/x/b000.jpg"}],
    }
    check = validate_scene_beats(scene, bundle)
    assert not check.ok
    assert any("missing file" in e for e in check.errors)


def test_validate_motion_beats_ok(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    frames = bundle / "frames" / "00-x"
    frames.mkdir(parents=True)
    (frames / "b000-k0.jpg").write_bytes(b"jpeg")
    (frames / "b000-k1.jpg").write_bytes(b"jpeg")
    (frames / "b001.jpg").write_bytes(b"jpeg")
    scene = {
        "id": "scene-0",
        "t0": 0.0,
        "t1": 16.0,
        "beat_mode": "human_curated_motion",
        "beats": [
            {
                "id": "b000",
                "kind": "motion",
                "t0": 0.0,
                "t1": 8.0,
                "keyframes": [
                    {"frame_t": 1.0, "path": "frames/00-x/b000-k0.jpg"},
                    {"frame_t": 5.0, "path": "frames/00-x/b000-k1.jpg"},
                ],
            },
            {"id": "b001", "t0": 8.0, "t1": 16.0, "path": "frames/00-x/b001.jpg", "frame_t": 12.0},
        ],
    }
    check = validate_scene_beats(scene, bundle)
    assert check.ok
