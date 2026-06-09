"""Batched run_sleep (CASA-ADR-0023 R1)."""

from __future__ import annotations

from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, hippo_episodes, run_sleep


def _mini_state() -> dict:
    n = 8 * 8
    lat = {"width": 8, "height": 8, "cells": [[] for _ in range(n)], "concept_prefix": "lang.word."}
    return ensure_prisms(
        {
            "field_version": 1,
            "sss": {"lattices": {"lexicon-ru": lat}, "active_lattice": "lexicon-ru"},
            "consolidation": {},
        }
    )


def test_run_sleep_max_episodes_defers_tail_until_drained():
    state = _mini_state()
    bundle: dict = {"claims": [], "graph": {"edges": []}}

    for i in range(3):
        append_episode(
            state,
            cue=f"cue{i}",
            surface_attempt="x",
            correct=f"w{i}",
            lattice_id="lexicon-ru",
            concept_id=f"lang.word.w{i}",
        )

    first = run_sleep(state, bundle, max_episodes=1)
    assert first["merged"] == 1
    assert first["pending"] == 2
    assert first.get("batch", {}).get("deferred_tail") is True
    assert first.get("z_compose") is None
    assert len(hippo_episodes(state)) == 2

    second = run_sleep(state, bundle, max_episodes=1)
    assert second["merged"] == 1
    assert len(hippo_episodes(state)) == 1

    third = run_sleep(state, bundle, max_episodes=1)
    assert third["merged"] == 1
    assert len(hippo_episodes(state)) == 0
    assert third.get("batch", {}).get("deferred_tail") is False
    assert third.get("z_compose") is not None


def test_run_sleep_max_episodes_none_matches_monolithic_count():
    state = _mini_state()
    bundle: dict = {"claims": [], "graph": {"edges": []}}
    append_episode(
        state,
        cue="a",
        surface_attempt="b",
        correct="c",
        lattice_id="lexicon-ru",
        concept_id="lang.word.c",
    )
    rep = run_sleep(state, bundle, max_episodes=None)
    assert rep["merged"] == 1
    assert len(hippo_episodes(state)) == 0
    assert "batch" not in rep
