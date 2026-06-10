#!/usr/bin/env python3
"""Defense zone + trauma life-event infer (ADR-0076)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from casa.prisms.affect import infer_life_event_from_turn, spawn_emotional_zone
from casa.prisms.defense.infer import infer_trauma_life_event
from casa.prisms.intelligence.defense_zone import (
    defense_core_block,
    ensure_defense_zone,
    migrate_legacy_defense_state,
    spawn_defense_zone,
)
from casa.prisms.memory.memory_prisms import ensure_prisms


class DefenseZoneInferTests(unittest.TestCase):
    def test_infer_caregiver_violation(self) -> None:
        event = infer_trauma_life_event("Отец душил меня — я не могла дышать.")
        self.assertEqual(event, "caregiver_violation")

    def test_infer_security_threat(self) -> None:
        event = infer_trauma_life_event("Меня ударили на улице — страх и боль.")
        self.assertEqual(event, "security_threat")

    def test_infer_from_turn_priority(self) -> None:
        state = ensure_prisms({"field_version": 0})
        spawn_emotional_zone(state)
        event = infer_life_event_from_turn(
            state,
            partner_text="Папа душил тебя в детстве?",
            subject_reply="",
            query_intent="discuss",
        )
        self.assertEqual(event, "caregiver_violation")

    def test_migrate_flat_defense_to_zone(self) -> None:
        state = ensure_prisms({"field_version": 0, "defense": {"repression_count": 3}})
        self.assertTrue(migrate_legacy_defense_state(state))
        self.assertNotIn("defense", state)
        core = defense_core_block(state)
        self.assertEqual(int(core.get("repression_count") or 0), 3)
        ensure_defense_zone(state)
        from casa.prisms.intelligence.model import intelligence_root

        self.assertIn("defense", intelligence_root(state))

    def test_spawn_defense_zone_lattices(self) -> None:
        state = ensure_prisms({"field_version": 0})
        rep = spawn_defense_zone(state)
        self.assertEqual(rep["core_lattice_id"], "agent-defense-core")
        self.assertEqual(rep["sandbox_lattice_id"], "agent-defense-sandbox")

    def test_defense_after_infer_integration(self) -> None:
        from casa.prisms.affect import affect_after_turn
        from casa.prisms.defense import defense_after_life_event

        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            state = ensure_prisms({"field_version": 0})
            spawn_emotional_zone(
                state,
                config={"initial_axes": {"valence": -0.4, "arousal": 0.6, "security": 0.2}},
            )
            event = infer_life_event_from_turn(
                state,
                partner_text="Отец душил — страх и боль.",
                subject_reply="",
            )
            self.assertEqual(event, "caregiver_violation")
            affect_after_turn(state, event, tick=9)
            rep = defense_after_life_event(state, store, life_event=event, tick=9)
            self.assertIn("trauma", rep)
            self.assertFalse(rep["trauma"].get("skipped"))


if __name__ == "__main__":
    unittest.main()
