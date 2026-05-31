"""run_sleep ↔ replay_buffer hook (CASA-ADR-0009)."""

from __future__ import annotations

import casa.prisms.hippo.replay_buffer as rb
from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, run_sleep


def _mini_state() -> dict:
    n = 8 * 8
    lat = {"width": 8, "height": 8, "cells": [[] for _ in range(n)], "concept_prefix": "lang.word."}
    return ensure_prisms(
        {
            "field_version": 1,
            "sss": {"lattices": {"L2_word": lat}, "active_lattice": "L2_word"},
            "consolidation": {},
        }
    )


def test_run_sleep_archives_prior_and_replays_on_second_sleep():
    state = _mini_state()
    bundle: dict = {"claims": [], "graph": {"edges": []}}

    append_episode(
        state,
        cue="согласно",
        surface_attempt="приказа",
        correct="приказу",
        lattice_id="L2_word",
        concept_id="lang.word.приказ",
        correction_kind="ortho_surface",
        scene="канцелярия",
    )
    first = run_sleep(state, bundle, replay_k=0)
    assert first["merged"] == 1
    assert len(rb.get_buffer(state)) == 0

    second = run_sleep(state, bundle, replay_k=1)
    assert second["replay"]["archived_new"] == 1
    assert second["replay"]["replayed"] == 1
    buf = rb.get_buffer(state)
    assert len(buf) == 1
    assert buf[0]["episode_id"] == first["items"][0]["episode_id"]
    assert buf[0]["replays"] == 1
    assert buf[0]["value"] == 1.0  # ortho_surface via lattice_value tag on archive
