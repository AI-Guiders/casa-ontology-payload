#!/usr/bin/env python3
"""Repair invite → compose bias; partner cues; zone scoring."""

from __future__ import annotations

import unittest

from casa.domain.dialogue_bind.zone_scoring import affect_bind_nudge, apply_intelligence_zone_block_deltas
from casa.prisms.affect import affect_after_turn, spawn_emotional_zone
from casa.prisms.intelligence.partner_cues import infer_partner_life_event_name, partner_says_thanks
from casa.prisms.intelligence.social import ensure_social_zone, spawn_social_zone
from casa.prisms.intelligence.tick import intelligence_before_partner_compose


class PartnerCuesTests(unittest.TestCase):
    def test_thanks_and_repair_invite(self) -> None:
        self.assertTrue(partner_says_thanks("Спасибо, помогло"))
        self.assertEqual(
            infer_partner_life_event_name("прости, это было неожиданно молчать"),
            "partner_repair_invite",
        )

    def test_trust_syncs_affect_and_social(self) -> None:
        state: dict = {}
        spawn_emotional_zone(state)
        spawn_social_zone(state)
        affect_after_turn(state, "partner_trust", tick=1)
        self.assertGreater(float(ensure_social_zone(state)["partner_trust"]), 0.5)


class ZoneScoringTests(unittest.TestCase):
    def test_honest_defer_nudge(self) -> None:
        state: dict = {}
        spawn_emotional_zone(state)
        affect_after_turn(state, "self_failure", tick=1)
        blocks = [
            {"concept_id": "ru.dialog.honest.short", "score": 10},
            {"concept_id": "ru.dialog.capabilities.list", "score": 20},
        ]
        apply_intelligence_zone_block_deltas(blocks, state, intent="social")
        self.assertGreater(blocks[0]["score"], blocks[1]["score"])

    def test_affect_bind_nudge_affinity(self) -> None:
        state: dict = {}
        spawn_emotional_zone(state)
        affect_after_turn(state, "partner_trust", tick=1)
        nudge = affect_bind_nudge(state, concept_id="ru.dialog.thanks", intent="social")
        self.assertGreater(nudge, 0)


class RepairComposeTests(unittest.TestCase):
    def test_before_compose_sets_repair_deltas(self) -> None:
        state: dict = {}
        spawn_emotional_zone(state)
        spawn_social_zone(state)
        intelligence_before_partner_compose(
            state,
            partner_text="прости, странно что молчал",
            query_intent="social",
            tick=3,
        )
        blocks = [{"concept_id": "subject.dialog.partner_recent", "score": 5}]
        apply_intelligence_zone_block_deltas(blocks, state, intent="social")
        self.assertGreaterEqual(blocks[0]["score"], 25)


if __name__ == "__main__":
    unittest.main()
