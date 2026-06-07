#!/usr/bin/env python3
"""Tests for Emotional Zone (ADR-0060)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from casa.domain.prism_wire import prism_agent
from casa.prisms.affect import (
    affect_after_turn,
    affect_compose_bias,
    core_affect_state,
    promote_sandbox_experiment,
    sandbox_record_experiment,
    spawn_emotional_zone,
)
from casa.prisms.memory.agent_prism import agent_lattices, load_agent_prism
from casa.prisms.memory.memory_prisms import ensure_prisms


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
        block = prism_agent(state)
        self.assertIn("emotional", block.get("intelligence_zones") or {})
        self.assertNotIn("emotional_zone", block)

    def test_legacy_emotional_zone_migrates_on_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            (store / "agent" / "lattices").mkdir(parents=True)
            state: dict = {}
            ensure_prisms(state)
            spawn_emotional_zone(state)
            affect_after_turn(state, "self_failure", tick=1)
            block = prism_agent(state)
            legacy = (block.get("intelligence_zones") or {}).pop("emotional")
            block["emotional_zone"] = legacy
            manifest = {
                "schema_version": 1,
                "kind": "agent_prism",
                "lattices": {},
                "nca": {"models": {}},
                "zone_state": {"emotional_zone": legacy},
            }
            (store / "agent" / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            fresh: dict = {}
            ensure_prisms(fresh)
            load_agent_prism(store, fresh)
            loaded = prism_agent(fresh)
            self.assertIn("emotional", loaded.get("intelligence_zones") or {})
            self.assertNotIn("emotional_zone", loaded)
            self.assertIn("dialog.repair_pending", core_affect_state(fresh).episodic)

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
