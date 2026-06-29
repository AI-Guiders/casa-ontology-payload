#!/usr/bin/env python3
"""Numeric value mutexes — «X больше/меньше/равно N ед» and disjoint-range contradictions.

A threshold parses to num_gt/num_lt/num_eq(subject, amount{value,unit}); two thresholds on
the same quantity contradict when their intervals are disjoint («>10» ∧ «<5», «>5» ∧ «=3»)
or their units clash (мл ↔ мг). Compatible thresholds («>5» ∧ «=10») are independent.
"""

from __future__ import annotations

import unittest

from casa.curriculum.parse import parse_triples
from casa.curriculum.reasoning import relate
from casa.curriculum.roundtrip import translate_through_meaning
from casa.curriculum.world import build_meaning_state


class ValueMutexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state, cls.lat = build_meaning_state()

    def verdict(self, a: str, b: str) -> str:
        return relate(self.state, self.lat, a, b)["verdict"]

    def classes(self, a: str, b: str) -> set[str]:
        return {c["class"] for c in relate(self.state, self.lat, a, b)["conflicts"]}

    def test_threshold_parses_both_languages(self) -> None:
        self.assertEqual(parse_triples(self.state, self.lat, "воды больше 5 мл"),
                         [("num_gt", "concept.water", "concept.amount")])
        self.assertEqual(parse_triples(self.state, self.lat, "the water is greater than 5 ml"),
                         [("num_gt", "concept.water", "concept.amount")])
        self.assertEqual(parse_triples(self.state, self.lat, "воды меньше 5 мл"),
                         [("num_lt", "concept.water", "concept.amount")])
        self.assertEqual(parse_triples(self.state, self.lat, "воды равно 5 мл"),
                         [("num_eq", "concept.water", "concept.amount")])

    def test_threshold_round_trip(self) -> None:
        tr = translate_through_meaning(self.state, self.lat, "воды больше 5 мл")
        self.assertEqual(tr["en"], "The water is greater than 5 ml.")

    def test_disjoint_ranges_contradict(self) -> None:
        self.assertEqual(self.verdict("воды больше 10 мл", "воды меньше 5 мл"), "contradicts")
        self.assertIn("range", self.classes("воды больше 10 мл", "воды меньше 5 мл"))
        self.assertEqual(self.verdict("воды равно 5 мл", "воды равно 10 мл"), "contradicts")
        self.assertEqual(self.verdict("воды больше 5 мл", "воды равно 3 мл"), "contradicts")

    def test_compatible_ranges_are_independent(self) -> None:
        self.assertEqual(self.verdict("воды больше 5 мл", "воды равно 10 мл"), "independent")
        self.assertEqual(self.verdict("воды больше 5 мл", "воды больше 10 мл"), "independent")

    def test_unit_mismatch_is_caught(self) -> None:
        self.assertEqual(self.verdict("воды равно 5 мл", "воды равно 5 мг"), "contradicts")
        self.assertIn("unit", self.classes("воды равно 5 мл", "воды равно 5 мг"))

    def test_object_comparison_unaffected(self) -> None:
        # «больше» + a noun is still the object comparison, not a numeric threshold
        self.assertEqual(parse_triples(self.state, self.lat, "слон больше мыши"),
                         [("bigger_than", "concept.elephant", "concept.mouse")])


if __name__ == "__main__":
    unittest.main()
