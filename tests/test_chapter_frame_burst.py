#!/usr/bin/env python3
"""Tests for chapter visual burst sampling."""

from __future__ import annotations

from casa.sensory.chapter_frame_burst import burst_frame_rel_paths, chapter_sample_times


def test_chapter_sample_times_spans_window() -> None:
    times = chapter_sample_times(0.0, 201.0, interval_sec=12.0, min_frames=4, max_frames=24)
    assert len(times) >= 4
    assert times[0] == 0.0
    assert abs(times[-1] - 201.0) < 0.01


def test_burst_frame_rel_paths() -> None:
    times = chapter_sample_times(10.0, 70.0, interval_sec=15.0, min_frames=3, max_frames=10)
    rows = burst_frame_rel_paths(chapter_index=0, slug="kolgotki", times=times, t0=10.0)
    assert len(rows) == len(times)
    assert rows[0]["path"].startswith("frames/00-kolgotki/f0000.jpg")
    assert rows[0]["t"] == 0.0
    assert rows[1]["t"] > 0.0
