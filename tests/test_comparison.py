#!/usr/bin/env python3
"""bigger_than — a comparison relation with transitive inference in the question."""

from __future__ import annotations

import unittest

from casa.curriculum.ask import answer_question
from casa.curriculum.converse import answer_clause
from casa.curriculum.parse import parse_graph, parse_triples
from casa.curriculum.roundtrip import translate_through_meaning
from casa.curriculum.world import build_meaning_state


class ComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state, cls.lat = build_meaning_state()

    def test_statement_is_a_relation(self) -> None:
        self.assertEqual(parse_triples(self.state, self.lat, "слон больше мыши"),
                         [("bigger_than", "concept.elephant", "concept.mouse")])

    def test_round_trip(self) -> None:
        tr = translate_through_meaning(self.state, self.lat, "слон больше мыши")
        self.assertEqual(tr["ru"], "Слон больше мыши.")          # soft-sign feminine genitive
        self.assertEqual(tr["en"], "The elephant is bigger than the mouse.")
        self.assertEqual(translate_through_meaning(self.state, self.lat, "the elephant is bigger than the mouse")["ru"],
                         "Слон больше мыши.")

    def test_non_sizable_is_refused(self) -> None:
        g = parse_graph(self.state, self.lat, "идея больше дома")  # an idea has no size
        self.assertFalse(any(e["satisfied"] for e in g["edges"]))

    def test_transitive_inference(self) -> None:
        state, lat = build_meaning_state()
        answer_clause(state, lat, "слон больше собаки")
        answer_clause(state, lat, "собака больше кошки")
        # never stated elephant > cat — derived through the chain
        self.assertEqual(answer_question(state, lat, "слон больше кошки?"), "Да, «слон» больше «кот».")

    def test_asymmetry(self) -> None:
        state, lat = build_meaning_state()
        answer_clause(state, lat, "слон больше собаки")
        self.assertTrue(answer_question(state, lat, "собака больше слона?").startswith("Нет, наоборот"))

    def test_unknown_is_honest(self) -> None:
        state, lat = build_meaning_state()
        self.assertIn("не знаю", answer_question(state, lat, "слон больше кошки?").lower())


if __name__ == "__main__":
    unittest.main()
