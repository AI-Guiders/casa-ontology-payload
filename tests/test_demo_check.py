#!/usr/bin/env python3
"""The curated validator demo runs end to end and keeps its triage verdicts."""

from __future__ import annotations

import unittest

from casa.curriculum.demo_check import render_check_demo
from casa.curriculum.world import build_meaning_state


class DemoCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state, cls.lat = build_meaning_state()
        cls.out = render_check_demo(cls.state, cls.lat)

    def test_shows_all_three_verdicts(self) -> None:
        self.assertIn("✅ ЭКВИВАЛЕНТНО", self.out)
        self.assertIn("⚠️ РАСХОЖДЕНИЕ", self.out)
        self.assertIn("❓ НЕПРОВЕРЯЕМО", self.out)

    def test_dangerous_classes_named(self) -> None:
        self.assertIn("[polarity]", self.out)
        self.assertIn("[quantity]", self.out)

    def test_correct_negation_not_false_flagged(self) -> None:
        # «не закрывай окно» / «do not close the window» must read as equivalent
        self.assertIn("не закрывай окно", self.out)
        self.assertNotIn("ОПАСНО: потеряно отрицание\n  источник: «не закрывай окно»", self.out)


if __name__ == "__main__":
    unittest.main()
