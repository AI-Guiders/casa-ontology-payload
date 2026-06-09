#!/usr/bin/env python3
"""Wake forgetting hooks on every tick (moral north star / ADR-0070)."""

from __future__ import annotations

import unittest

from casa.domain.prism_wire import prism_hippo
from casa.prisms.memory.agent_prism import ensure_agent_prism
from casa.prisms.memory.forgetting import memory_wake_forgetting_hooks
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.zone import spawn_memory_zone


class MemoryWakeForgettingTests(unittest.TestCase):
    def _state(self) -> dict:
        state = ensure_prisms({"field_version": 8})
        ensure_agent_prism(state)
        spawn_memory_zone(state)
        return state

    def test_wake_hooks_run_priming_every_tick(self) -> None:
        state = self._state()
        rep = memory_wake_forgetting_hooks(state, tick=3)
        self.assertIn("priming_decay", rep)
        self.assertEqual(rep["tick"], 3)
        self.assertIn("wake_last", state.get("forgetting") or {})

    def test_wake_hooks_episodic_on_schedule(self) -> None:
        state = self._state()
        rep = memory_wake_forgetting_hooks(state, tick=8)
        self.assertIsNotNone(rep.get("episodic_fade"))
        hippo = prism_hippo(state)
        if hippo.get("episodes"):
            self.assertIn("salience", hippo["episodes"][0])


if __name__ == "__main__":
    unittest.main()
