#!/usr/bin/env python3
"""Validator reality-check harness — coverage on curated pairs, recall on dangerous errors."""

from __future__ import annotations

import unittest

from casa.curriculum.reality_check import (
    CURATED_PAIRS,
    RECALL_CASES,
    ceiling_report,
    coverage_report,
    recall_report,
)
from casa.curriculum.world import build_meaning_state


class RealityCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state, cls.lat = build_meaning_state()

    def test_curated_pairs_fully_covered(self) -> None:
        # the curated pairs are deliberately in supported forms -> both sides parse
        cov = coverage_report(self.state, self.lat, CURATED_PAIRS)
        self.assertEqual(cov["both"], cov["total"])
        self.assertEqual(cov["coverage"], 1.0)

    def test_recall_catches_every_dangerous_error(self) -> None:
        rec = recall_report(self.state, self.lat, RECALL_CASES)
        self.assertEqual(rec["tested"], len(RECALL_CASES))   # all parse (no coverage gap)
        self.assertEqual(rec["caught"], rec["tested"])       # 100% recall on the kernel
        self.assertEqual(rec["misses"], [])

    def test_recall_spans_all_three_classes(self) -> None:
        rec = recall_report(self.state, self.lat, RECALL_CASES)
        self.assertIn("polarity", rec["per_class"])
        self.assertIn("quantity", rec["per_class"])
        self.assertIn("unit", rec["per_class"])

    def test_ceiling_on_curated_is_full(self) -> None:
        # curated pairs are deliberately in supported forms: every side carries a relation,
        # so NOTHING is structurally out of reach -> ceiling is 100% and all pairs parse.
        cei = ceiling_report(self.state, self.lat, CURATED_PAIRS)
        self.assertEqual(cei["both_ceiling"], 0)       # no bare-label side
        self.assertEqual(cei["max_coverage"], 1.0)     # all addressable
        self.assertEqual(cei["both"], cei["total"])    # and all actually parse now

    def test_ceiling_flags_a_bare_label_side(self) -> None:
        # a pair with one bare-label side (no relation word) is structurally unreachable:
        # it is NOT addressable no matter how good the parser gets.
        cei = ceiling_report(self.state, self.lat, [("Configuration", "Настройки")])
        self.assertEqual(cei["addressable"], 0)
        self.assertEqual(cei["max_coverage"], 0.0)


if __name__ == "__main__":
    unittest.main()
