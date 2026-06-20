#!/usr/bin/env python3
"""Auditory listen imprint — cochlear stub + scene binding (ADR-0028 v0)."""

from __future__ import annotations

from pathlib import Path

from casa.domain.auditory_tract import LATTICE_AUDIO_BINAURAL, LATTICE_AUDIO_SPECTRUM
from casa.domain.prism_ids import PRISM_AUDITORY
from casa.domain.prism_wire import prism_block
from casa.prisms.memory.listen_moment import listen_moment
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.prism_spawn import spawn_content_lattice
from casa.sensory.load_wav import write_synthetic_contour_wav


def _minimal_state() -> dict:
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    spawn_content_lattice(state, "prism_memory", "L3_phrase", z_level=3)
    spawn_content_lattice(state, "prism_memory", "L2_word", z_level=2)
    return state


def test_listen_moment_auditory_and_lexical(tmp_path: Path) -> None:
    wav = tmp_path / "masha.wav"
    write_synthetic_contour_wav(wav)
    state = _minimal_state()
    moment = listen_moment(
        state,
        {
            "id": "masha-0001",
            "caption": "Маша сказала",
            "words": ["маша", "сказала"],
            "speaker": "masha",
        },
        wav_path=wav,
        copies=3,
    )

    recalled = [row["word"] for row in moment["recalled_words"]]
    assert "маша" in recalled
    assert "сказала" in recalled

    tokens = moment["auditory_tokens"]
    assert any(t.startswith("A:energy:") for t in tokens)
    assert any(t.startswith("A:dyn:rise") for t in tokens)
    assert "A:scene:masha-0001" in tokens

    block = prism_block(state, PRISM_AUDITORY)
    lat = (block.get("lattices") or {}).get(LATTICE_AUDIO_SPECTRUM) or {}
    flat = [tok for cell in (lat.get("cells") or []) for tok in cell]
    assert "A:scene:masha-0001" in flat


def test_cochlear_contour_has_rise_tokens(tmp_path: Path) -> None:
    wav = tmp_path / "rise.wav"
    write_synthetic_contour_wav(wav, duration_sec=0.6, base_freq=180.0)
    state = _minimal_state()
    moment = listen_moment(
        state,
        {"id": "dyn-test", "caption": "test", "words": ["test"]},
        wav_path=wav,
    )
    assert any(t == "A:dyn:rise" for t in moment["auditory_tokens"])


def test_stereo_keeps_lr_channels_and_pan(tmp_path: Path) -> None:
    wav = tmp_path / "stereo_left.wav"
    write_synthetic_contour_wav(wav, stereo=True, pan=-0.8)
    state = _minimal_state()
    moment = listen_moment(
        state,
        {"id": "stereo-test", "words": ["test"], "speaker": "masha"},
        wav_path=wav,
    )
    tokens = moment["auditory_tokens"]
    assert "A:layout:stereo" in tokens
    assert any(t.startswith("A:energy:L:") for t in tokens)
    assert any(t.startswith("A:energy:R:") for t in tokens)
    assert "A:pan:left" in tokens
    assert any(t.startswith("A:itd:") for t in tokens)
    assert any(t.startswith("A:ild:") for t in tokens)


def test_vocalization_no_lexical_words_medved_grunt(tmp_path: Path) -> None:
    wav = tmp_path / "medved.wav"
    write_synthetic_contour_wav(wav, stereo=True, pan=0.3, base_freq=90.0)
    state = _minimal_state()
    moment = listen_moment(
        state,
        {
            "id": "medved-grunt-001",
            "speaker": "medved",
        },
        wav_path=wav,
    )
    assert moment["recalled_words"] == []
    assert moment["lexical"]["kind"] == "anchor"
    assert any(t.startswith("A:energy:") for t in moment["auditory_tokens"])
    block = prism_block(state, PRISM_AUDITORY)
    assert LATTICE_AUDIO_BINAURAL in (block.get("lattices") or {})
