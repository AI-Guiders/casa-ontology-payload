#!/usr/bin/env python3
"""Tests for Emotional Zone (ADR-0060)."""

from __future__ import annotations

import unittest

from casa.prisms.affect import (
    affect_after_turn,
    affect_compose_bias,
    core_affect_state,
    promote_sandbox_experiment,
    sandbox_record_experiment,
    spawn_emotional_zone,
)
from casa.prisms.memory.agent_prism import agent_lattices


class EmotionalZoneTests(unittest.TestCase):
    def test_spawn_creates_core_and_sandbox_lattices(self) -> None:
        state: dict = {}
        rep = spawn_emotional_zone(state, tick=0)
        lats = agent_lattices(state)
        self.assertIn(rep["core_lattice_id"], lats)
        self.assertIn(rep["sandbox_lattice_id"], lats)
        core = core_affect_state(state)
        self.assertAlmostEqual(core.axes.valence, 0.0)
        self.assertAlmostEqual(core.axes.arousal, 0.2)
        self.assertAlmostEqual(core.axes.security, 0.5)

    def test_sandbox_does_not_touch_core_until_promote(self) -> None:
        state: dict = {}
        spawn_emotional_zone(state)
        before = core_affect_state(state).axes.to_dict()
        sandbox_record_experiment(
            state,
            deltas={"valence": 0.5, "security": 0.3},
            tick=1,
            note="try openness",
            score=0.9,
        )
        after = core_affect_state(state).axes.to_dict()
        self.assertEqual(before, after)
        promoted = promote_sandbox_experiment(state, "exp-1")
        self.assertIsNotNone(promoted)
        self.assertGreater(core_affect_state(state).axes.valence, before["valence"])

    def test_life_event_self_failure_sets_repair_pending(self) -> None:
        state: dict = {}
        spawn_emotional_zone(state)
        affect_after_turn(state, "self_failure", tick=3)
        core = core_affect_state(state)
        self.assertIn("dialog.repair_pending", core.episodic)
        self.assertLess(core.axes.valence, 0.0)
        bias = affect_compose_bias(state)
        self.assertTrue(bias["repair_pending"])

    def test_promote_requires_score(self) -> None:
        state: dict = {}
        spawn_emotional_zone(state)
        sandbox_record_experiment(state, deltas={"valence": 0.2}, score=0.1)
        self.assertIsNone(promote_sandbox_experiment(state, "exp-1"))


if __name__ == "__main__":
    unittest.main()
