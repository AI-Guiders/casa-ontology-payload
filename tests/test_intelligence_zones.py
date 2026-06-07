#!/usr/bin/env python3
"""Tests for Intelligence Zones P0–P5 (ADR-0061)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from casa.prisms.intelligence.apply import intelligence_compose_deltas, intelligence_tract_boosts
from casa.prisms.intelligence.migrate import migrate_intelligence_zones
from casa.prisms.intelligence.tick import process_intelligence_turn
from casa.prisms.memory.agent_prism import agent_lattices, ensure_agent_prism, load_agent_prism
from casa.prisms.memory.bootstrap_agent_manifest import load_agent_bootstrap_manifest
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.tick.tract.competition import compete_tract_intent


class IntelligenceZonesTests(unittest.TestCase):
    def test_migrate_spawns_all_enabled_zones(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            (store / "bundles").mkdir(parents=True)
            rep = migrate_intelligence_zones(store, tick=1)
            boot = boot_store(store, prefer_field_state=True)
            load_agent_prism(store, boot["state"])
            lats = agent_lattices(boot["state"])
            for lid in (
                "agent-limbic-core",
                "agent-affect-sandbox",
                "agent-exec-core",
                "agent-exec-sandbox",
                "agent-social-core",
                "agent-social-sandbox",
                "agent-logical-core",
                "agent-logical-sandbox",
                "agent-character-core",
                "agent-metabolic-core",
                "agent-percept-core",
                "agent-linguistic-core",
            ):
                self.assertIn(lid, lats, lid)
            self.assertNotIn("agent-spatial-core", lats)
            self.assertEqual(rep["intelligence_zones_version"], 4)

    def test_logical_tract_boosts_math_on_arithmetic(self) -> None:
        from casa.prisms.intelligence.logical import spawn_logical_zone

        state: dict = {}
        spawn_logical_zone(state)
        boosts = intelligence_tract_boosts(state, concept_hints=["math.add"])
        self.assertGreater(boosts.get("math", 0), boosts.get("social", 0))

    def test_repair_compose_deltas_deprioritize_capabilities(self) -> None:
        from casa.prisms.affect import affect_after_turn, spawn_emotional_zone
        from casa.prisms.intelligence.social import spawn_social_zone

        state: dict = {}
        spawn_emotional_zone(state)
        spawn_social_zone(state)
        affect_after_turn(state, "self_failure", tick=1)
        deltas = intelligence_compose_deltas(state)
        self.assertLess(deltas.get("ru.dialog.capabilities", 0), 0)
        self.assertGreater(deltas.get("subject.dialog.partner_recent", 0), 0)

    def test_process_turn_updates_snapshot(self) -> None:
        state: dict = {}
        ensure_agent_prism(state)
        from casa.prisms.affect import spawn_emotional_zone
        from casa.prisms.intelligence.executive import spawn_executive_zone
        from casa.prisms.intelligence.social import spawn_social_zone

        spawn_emotional_zone(state)
        spawn_executive_zone(state)
        spawn_social_zone(state)
        snap = process_intelligence_turn(
            state,
            partner_text="прости, это было неожиданно",
            subject_reply="",
            query_intent="social",
            tick=3,
        )
        self.assertIn("emotional", snap)
        self.assertIn("social", snap)
        self.assertEqual(snap.get("life_event"), "partner_repair_invite")

    def test_compete_tract_uses_intelligence_boosts(self) -> None:
        state: dict = {}
        from casa.prisms.intelligence.executive import spawn_executive_zone
        from casa.prisms.intelligence.logical import spawn_logical_zone

        spawn_executive_zone(state)
        spawn_logical_zone(state)
        intent, ranked = compete_tract_intent("5+7", None, state=state)
        math_score = next(t.score for t in ranked if t.tract_id == "math")
        social_score = next(t.score for t in ranked if t.tract_id == "social")
        self.assertGreater(math_score, social_score)
        self.assertEqual(intent, "math")


if __name__ == "__main__":
    unittest.main()
