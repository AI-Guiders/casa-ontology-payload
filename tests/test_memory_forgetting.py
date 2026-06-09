#!/usr/bin/env python3
"""Memory priming decay + implicit gains (ADR-0068 P12d / ADR-0070 P15b)."""

from __future__ import annotations

import unittest

from casa.prisms.intelligence.scope_bind import apply_bind_scope
from casa.prisms.memory.forgetting import (
    DEFAULT_PRIMING_ALPHA,
    memory_implicit_gains,
    memory_priming_decay,
    memory_priming_record_bind,
    memory_priming_touch,
)
from casa.prisms.memory.agent_prism import ensure_agent_prism
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.zone import ensure_memory_zone, spawn_memory_zone


class MemoryForgettingTests(unittest.TestCase):
    def _state(self) -> dict:
        state = ensure_prisms({"field_version": 1})
        ensure_agent_prism(state)
        spawn_memory_zone(state)
        return state

    def test_priming_decays_without_rebind(self) -> None:
        state = self._state()
        memory_priming_touch(state, ["math.num.three", "lang.word.привет"], tick=1, weight=1.0)
        rep = memory_priming_decay(state, tick=2)
        self.assertEqual(rep["alpha_retain"], DEFAULT_PRIMING_ALPHA)
        self.assertEqual(rep["active_count"], 2)
        rep2 = memory_priming_decay(state, tick=3)
        self.assertEqual(rep2["active_count"], 2)
        cells = ensure_memory_zone(state)["implicit"]["priming"]["cells"]
        self.assertAlmostEqual(cells["math.num.three"], DEFAULT_PRIMING_ALPHA**2, places=5)

    def test_priming_fades_after_several_ticks(self) -> None:
        state = self._state()
        memory_priming_touch(state, ["concept.a"], tick=0, weight=1.0)
        for t in range(1, 8):
            memory_priming_decay(state, tick=t)
        cells = ensure_memory_zone(state)["implicit"]["priming"]["cells"]
        self.assertNotIn("concept.a", cells)

    def test_record_bind_boosts_and_refreshes_winners(self) -> None:
        state = self._state()
        memory_priming_touch(state, ["math.op.add"], tick=1, weight=0.8)
        blocks = [
            {"concept_id": "math.op.add", "score": 10, "text": "add"},
            {"concept_id": "math.num.two", "score": 3, "text": "two"},
        ]
        rep = memory_priming_record_bind(state, blocks, tick=2, min_score=5)
        self.assertGreaterEqual(rep["boosted"], 1)
        self.assertGreaterEqual(blocks[0]["score"], 10)
        self.assertIn("math.op.add", ensure_memory_zone(state)["implicit"]["priming"]["cells"])

    def test_implicit_gains_vary_by_tract(self) -> None:
        state = self._state()
        math_gains = memory_implicit_gains(state, tract="math")
        social_gains = memory_implicit_gains(state, tract="social")
        self.assertGreater(math_gains["procedural_scale"], 1.0)
        self.assertGreater(social_gains["priming_scale"], math_gains["priming_scale"])

    def test_apply_bind_scope_sets_implicit_gains(self) -> None:
        state = self._state()
        state["meta"] = {"zone_lattice_index": {"schema-math": {"domain": "math", "owner_zone": "memory"}}}
        rep = apply_bind_scope(state, tract="math", client_zone="logical")
        self.assertIn("implicit_gains", rep)
        self.assertEqual(state["meta"]["memory_implicit_gains"]["tract"], "math")


if __name__ == "__main__":
    unittest.main()
