#!/usr/bin/env python3
"""Tests for online womb tick fingerprints."""

from __future__ import annotations

from casa.domain.listen_womb_tick import fingerprint_delta, sample_stream_times, visual_token_fingerprint
from casa.sensory.rgb_frame import RgbFrame


def _solid_frame(r: int, g: int, b: int) -> RgbFrame:
    return RgbFrame(width=32, height=32, rgb=bytes([r, g, b] * 32 * 32))


def test_fingerprint_delta_identical() -> None:
    a = visual_token_fingerprint(_solid_frame(40, 80, 120))
    b = visual_token_fingerprint(_solid_frame(40, 80, 120))
    assert fingerprint_delta(a, b) == 0.0


def test_fingerprint_delta_changed() -> None:
    a = visual_token_fingerprint(_solid_frame(10, 10, 10))
    b = visual_token_fingerprint(_solid_frame(240, 240, 240))
    assert fingerprint_delta(a, b) > 0.2


def test_sample_stream_times() -> None:
    times = sample_stream_times(8.0, 10.0, interval_sec=0.5)
    assert times[0] == 8.0
    assert times[-1] == 10.0
    assert len(times) == 5
