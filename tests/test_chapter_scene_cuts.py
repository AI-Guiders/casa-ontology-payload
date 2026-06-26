#!/usr/bin/env python3
"""Tests for scene-cut beat windows (no ffmpeg)."""

from __future__ import annotations

from casa.sensory.chapter_scene_cuts import cuts_to_beat_windows, merge_close_cuts


def test_merge_close_cuts() -> None:
    assert merge_close_cuts([0.0, 1.0, 5.0, 6.0, 20.0], min_gap_sec=2.0) == [0.0, 5.0, 20.0]


def test_cuts_to_beat_windows_covers_chapter() -> None:
    beats = cuts_to_beat_windows([5.0, 50.0, 100.0], t0=0.0, t1=120.0, min_beats=3)
    assert beats[0][0] == 0.0
    assert abs(beats[-1][1] - 120.0) < 0.01
    assert all(b[1] > b[0] for b in beats)
