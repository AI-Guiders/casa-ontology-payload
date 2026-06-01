"""Ingest episodic policy (CASA-ADR-0023 R3)."""

from __future__ import annotations

from casa.prisms.memory.ingest_episodic import (
    record_listen_surface,
    resolve_ingest_episodic_mode,
    set_ingest_episodic_mode,
)
from casa.prisms.memory.memory_prisms import ensure_prisms, hippo_episodes


def _state() -> dict:
    return ensure_prisms({"field_version": 1, "sss": {"lattices": {}}, "store": {}})


def test_ingest_mode_off_skips_listen_episode() -> None:
    state = _state()
    set_ingest_episodic_mode(state, "off")
    assert resolve_ingest_episodic_mode(state) == "off"
    ep = record_listen_surface(
        state,
        cue="привет",
        surface_attempt="x",
        correct="привет",
        lattice_id="L2_word",
        concept_id="lang.word.привет",
    )
    assert ep is None
    assert len(hippo_episodes(state)) == 0


def test_ingest_mode_surprise_only_allows_correction() -> None:
    state = _state()
    set_ingest_episodic_mode(state, "surprise_only")
    assert (
        record_listen_surface(
            state,
            cue="a",
            surface_attempt="b",
            correct="c",
            lattice_id="L2_word",
            correction_kind="ortho_surface",
        )
        is not None
    )
    assert len(hippo_episodes(state)) == 1


def test_ingest_mode_full_records_listen() -> None:
    state = _state()
    set_ingest_episodic_mode(state, "full")
    record_listen_surface(
        state,
        cue="a",
        surface_attempt="b",
        correct="c",
        lattice_id="L2_word",
    )
    assert len(hippo_episodes(state)) == 1
