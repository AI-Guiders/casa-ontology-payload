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


def test_modality_tags_for_stream_tick() -> None:
    from casa.domain.listen_womb_tick import _modality_tags_for_stream_tick

    assert _modality_tags_for_stream_tick(audio_active=True, visual_delta=0.1) == [
        "auditory",
        "visual",
    ]
    assert _modality_tags_for_stream_tick(audio_active=False, visual_delta=0.0) == []


def test_hippo_index_summary_empty() -> None:
    from casa.domain.listen_womb_tick import _hippo_index_summary

    rep = _hippo_index_summary({})
    assert rep["journal_len"] == 0
    assert rep["moment_buffer_count"] == 0
