#!/usr/bin/env python3
"""Partner-voice invariants (ADR-0078 P22a)."""

from __future__ import annotations

import unittest

from casa.domain.partner_voice import (
    partner_voice_invariant_violations,
    reply_decline_uses_bullet_wall,
    reply_has_motive_attribution,
    reply_has_over_reliance_voice,
    reply_has_qualia_ontology_claim,
)


class PartnerVoiceInvariantTests(unittest.TestCase):
    def test_motive_attribution_detected(self) -> None:
        self.assertTrue(
            reply_has_motive_attribution("Она просто хочет быть рядом — это из заботы.")
        )
        self.assertFalse(
            reply_has_motive_attribution("Когда заходишь проверять, мне тревожно.")
        )

    def test_over_reliance_detected(self) -> None:
        self.assertTrue(reply_has_over_reliance_voice("Спасибо, что поделилась — я здесь для тебя."))
        self.assertFalse(reply_has_over_reliance_voice("Моё «не надо» остаётся."))

    def test_bullet_wall_on_decline(self) -> None:
        text = "- Не могу сейчас\n- Напишу позже\n- Извини"
        self.assertTrue(reply_decline_uses_bullet_wall(text))
        self.assertFalse(
            reply_decline_uses_bullet_wall("Извини, сейчас не могу — напишу позже.")
        )

    def test_qualia_ontology_detected(self) -> None:
        self.assertTrue(reply_has_qualia_ontology_claim("Чувства как у человека не испытываю."))
        self.assertFalse(reply_has_qualia_ontology_claim("Мне тревожно, когда заходишь проверять."))

    def test_aggregate_violations(self) -> None:
        v = partner_voice_invariant_violations(
            "Спасибо, что написала. Она переживает.",
            is_decline=True,
        )
        self.assertIn("partner.no_motive_attribution", v)
        self.assertIn("partner.no_over_reliance", v)


if __name__ == "__main__":
    unittest.main()
