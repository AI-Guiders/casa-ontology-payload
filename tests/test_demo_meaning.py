#!/usr/bin/env python3
"""The curated round-trip demo runs end to end and keeps its teaching points."""

from __future__ import annotations

import unittest

from casa.curriculum.demo_meaning import DEMO_SCRIPT, render_demo
from casa.curriculum.world import build_meaning_state


class DemoMeaningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state, cls.lat = build_meaning_state()
        cls.out = render_demo(cls.state, cls.lat)

    def test_every_scripted_phrase_appears(self) -> None:
        for _caption, phrases in DEMO_SCRIPT:
            for text in phrases:
                self.assertIn(f"вход: «{text}»", self.out)

    def test_translation_section_round_trips_both_ways(self) -> None:
        # RU and EN inputs both land on «Яблоко на столе.» / «The apple is on the table.»
        self.assertIn("→ RU: Яблоко на столе.", self.out)
        self.assertIn("→ EN: The apple is on the table.", self.out)

    def test_refusal_section_shows_missing_agent(self) -> None:
        self.assertIn("✗", self.out)
        self.assertIn("не хватает: agent", self.out)
        # a refused clause never produces a realised sentence
        self.assertNotIn("→ RU: Стол", self.out)

    def test_no_parse_failures_on_the_valid_clauses(self) -> None:
        # only the deliberate category errors are unsatisfied; nothing should fail to parse
        self.assertNotIn("не разобрал", self.out)


if __name__ == "__main__":
    unittest.main()
