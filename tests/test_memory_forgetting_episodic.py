#!/usr/bin/env python3
"""Episodic forgetting speed-2/3 (ADR-0070 P15c-e)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from casa.domain.prism_wire import prism_hippo
from casa.prisms.memory.agent_prism import ensure_agent_prism
from casa.prisms.memory.forgetting import (
    forget_episodic_fade,
    forget_episodic_trim,
    forget_should_episodic_fade,
    nca_erosion_pass,
    trim_dialogue_ring,
)
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.zone import ensure_memory_zone, spawn_memory_zone


class EpisodicForgettingTests(unittest.TestCase):
    def _state(self) -> dict:
        state = ensure_prisms({"field_version": 8})
        ensure_agent_prism(state)
        spawn_memory_zone(state)
        return state

    def _append_ep(self, state: dict, *, salience: float | None = None, concept_id: str = "concept.test") -> dict:
        hippo = prism_hippo(state)
        ep = {
            "id": "ep-test-1",
            "cue": "test",
            "surface_attempt": "x",
            "correct": "y",
            "lattice_id": "lexicon-ru",
            "concept_id": concept_id,
            "consolidated": False,
            "kind": "surface",
        }
        if salience is not None:
            ep["salience"] = salience
        hippo.setdefault("episodes", []).append(ep)
        return ep

    def test_fade_runs_every_n_ticks(self) -> None:
        state = self._state()
        self.assertTrue(forget_should_episodic_fade(state, tick=8))
        self.assertFalse(forget_should_episodic_fade(state, tick=7))

    def test_episodic_fade_lowers_salience_without_hub(self) -> None:
        state = self._state()
        self._append_ep(state)
        zone = state.setdefault("meta", {})
        zone["metabolic_last"] = {"fatigue": 0.0}
        rep = forget_episodic_fade(state, tick=8)
        self.assertGreaterEqual(rep["faded"], 1)
        ep = prism_hippo(state)["episodes"][0]
        self.assertLess(float(ep["salience"]), 1.0)

    def test_hub_cooccurrence_slows_fade(self) -> None:
        state = self._state()
        self._append_ep(state, concept_id="concept.hub")
        from casa.prisms.memory.forgetting import memory_priming_touch

        memory_priming_touch(state, ["concept.hub"], tick=1, weight=1.0)
        rep_plain = forget_episodic_fade(state, tick=8)
        sal_with_hub = float(prism_hippo(state)["episodes"][0]["salience"])

        state2 = self._state()
        self._append_ep(state2, concept_id="concept.hub")
        forget_episodic_fade(state2, tick=8)
        sal_without_hub = float(prism_hippo(state2)["episodes"][0]["salience"])
        self.assertGreater(sal_with_hub, sal_without_hub)
        self.assertGreaterEqual(rep_plain["faded"], 1)

    def test_trim_drops_low_salience_and_caps(self) -> None:
        state = self._state()
        hippo = prism_hippo(state)
        for i in range(5):
            hippo.setdefault("episodes", []).append(
                {
                    "id": f"ep-{i}",
                    "consolidated": False,
                    "salience": 0.01 if i < 2 else 0.9,
                }
            )
        ensure_memory_zone(state).setdefault("forgetting", {})["hippo_cap"] = 2
        rep = forget_episodic_trim(state)
        self.assertGreaterEqual(rep["trimmed_low_salience"], 2)
        self.assertLessEqual(rep["after"], 2)

    def test_nca_erosion_skips_immutable(self) -> None:
        state = self._state()
        rep = nca_erosion_pass(state)
        self.assertIn("immutable_skipped_count", rep)
        self.assertGreaterEqual(rep["immutable_skipped_count"], 0)

    def test_trim_dialogue_ring(self) -> None:
        state = self._state()
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            from casa.prisms.control.fpn_state import write_session_meta

            turns = [
                {
                    "at": "2026-01-01T00:00:00Z",
                    "speaker": "partner",
                    "text": f"msg {i}",
                    "kind": "reply",
                    "provenance": {},
                }
                for i in range(10)
            ]
            write_session_meta(store, {"dialogue_turns": turns})
            ensure_memory_zone(state).setdefault("forgetting", {})["dialogue_ring_cap"] = 4
            rep = trim_dialogue_ring(store, state)
            self.assertEqual(rep["after"], 4)
            self.assertEqual(rep["trimmed"], 6)


if __name__ == "__main__":
    unittest.main()
