#!/usr/bin/env python3
"""Validator reality-check harness — coverage on curated pairs, recall on dangerous errors."""

from __future__ import annotations

import unittest

from casa.curriculum.reality_check import (
    CURATED_PAIRS,
    RECALL_CASES,
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


if __name__ == "__main__":
    unittest.main()
