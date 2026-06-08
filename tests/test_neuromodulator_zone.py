#!/usr/bin/env python3
"""Neuromodulator Zone probes (ADR-0066 P10)."""

from __future__ import annotations

import unittest

from casa.prisms.affect import affect_after_turn, spawn_emotional_zone
from casa.prisms.neuromodulator import (
    neuromodulator_after_event,
    neuromodulator_begin_tick,
    neuromodulator_snapshot,
    spawn_neuromodulator_zone,
)


class NeuromodulatorZoneTests(unittest.TestCase):
    def test_self_failure_elevated_after_idle_decay(self) -> None:
        state: dict = {}
        spawn_emotional_zone(state)
        spawn_neuromodulator_zone(state)
        baseline = float(neuromodulator_snapshot(state)["arousal_drive"])

        neuromodulator_after_event(state, "self_failure", tick=1)
        affect_after_turn(state, "self_failure", tick=1)
        after_event = float(neuromodulator_snapshot(state)["arousal_drive"])
        self.assertGreater(after_event, baseline + 0.15)

        for tick in (2, 3, 4):
            neuromodulator_begin_tick(state, tick=tick, surprise_n=0, idle=True)
        still_elevated = float(neuromodulator_snapshot(state)["arousal_drive"])
        self.assertGreater(still_elevated, baseline + 0.1)

    def test_partner_trust_lowers_threat(self) -> None:
        state: dict = {}
        spawn_neuromodulator_zone(state)
        neuromodulator_after_event(state, "self_failure", tick=1)
        before = float(neuromodulator_snapshot(state)["threat_tone"])
        neuromodulator_after_event(state, "partner_trust", tick=2)
        after = float(neuromodulator_snapshot(state)["threat_tone"])
        self.assertLess(after, before)

    def test_spawn_creates_lattices(self) -> None:
        state: dict = {}
        spawn_neuromodulator_zone(state)
        from casa.prisms.memory.agent_prism import agent_lattices

        lats = agent_lattices(state)
        self.assertIn("agent-neuromod-core", lats)
        self.assertIn("agent-neuromod-sandbox", lats)


if __name__ == "__main__":
    unittest.main()
