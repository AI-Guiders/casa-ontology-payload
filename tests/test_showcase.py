#!/usr/bin/env python3
"""The unified showcase + dialogue-loop demo run end to end and keep their key results."""

from __future__ import annotations

import unittest

from casa.curriculum.demo_ask import render_ask_demo
from casa.curriculum.showcase import render_showcase
from casa.curriculum.world import build_meaning_state


class AskDemoTests(unittest.TestCase):
    def test_loop_states_then_answers_from_the_graph(self) -> None:
        state, lat = build_meaning_state()
        out = render_ask_demo(state, lat)
        self.assertIn("На столе: яблоко, книга.", out)        # location recall (names, not tokens)
        self.assertIn("Стол сделан из древесины.", out)        # material recall
        self.assertIn("Яблоко красное.", out)                  # colour recall
        self.assertIn("Да, «слон» больше «кот».", out)         # transitive comparison


class ShowcaseTests(unittest.TestCase):
    def test_all_three_pillars_present(self) -> None:
        state, lat = build_meaning_state()
        out = render_showcase(state, lat)
        self.assertIn("1. ROUND-TRIP", out)
        self.assertIn("2. ВОПРОСЫ", out)
        self.assertIn("3. ВАЛИДАТОР", out)
        # a sample from each pillar
        self.assertIn("→ EN: The apple is on the table.", out)   # round-trip
        self.assertIn("Нейманн:", out)                            # questions
        self.assertIn("⚠️ РАСХОЖДЕНИЕ", out)                      # validator catches a divergence


if __name__ == "__main__":
    unittest.main()
