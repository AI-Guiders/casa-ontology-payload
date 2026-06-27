#!/usr/bin/env python3
"""color_of relation — «яблоко красное» (predicate) and «какого цвета X?» (question)."""

from __future__ import annotations

import unittest

from casa.curriculum.ask import answer_question
from casa.curriculum.converse import answer_clause
from casa.curriculum.parse import parse_graph, parse_triples
from casa.curriculum.roundtrip import translate_through_meaning
from casa.curriculum.world import build_meaning_state


class ColorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state, cls.lat = build_meaning_state()

    def test_predicative_color_is_a_relation(self) -> None:
        self.assertEqual(parse_triples(self.state, self.lat, "яблоко красное"),
                         [("color_of", "concept.apple", "concept.red")])

    def test_predicative_round_trip(self) -> None:
        tr = translate_through_meaning(self.state, self.lat, "яблоко красное")
        self.assertEqual(tr["ru"], "Яблоко красное.")            # neuter agreement
        self.assertEqual(tr["en"], "The apple is red.")
        self.assertEqual(translate_through_meaning(self.state, self.lat, "the apple is red")["ru"], "Яблоко красное.")

    def test_non_colorable_is_refused(self) -> None:
        g = parse_graph(self.state, self.lat, "идея красная")  # an idea has no colour
        self.assertFalse(any(e["satisfied"] for e in g["edges"]))

    def test_attributive_color_is_still_an_attribute(self) -> None:
        g = parse_graph(self.state, self.lat, "красное яблоко на столе")
        self.assertEqual(g["nodes"]["concept.apple"].get("attrs"), ["red"])

    def test_question_after_predicative_statement(self) -> None:
        state, lat = build_meaning_state()  # fresh memory
        answer_clause(state, lat, "стол белый")
        self.assertEqual(answer_question(state, lat, "какого цвета стол?"), "Стол белый.")

    def test_question_from_attributive_memory(self) -> None:
        state, lat = build_meaning_state()
        answer_clause(state, lat, "красная книга на столе")
        self.assertEqual(answer_question(state, lat, "какого цвета книга?"), "Книга красная.")

    def test_question_unknown_is_honest(self) -> None:
        state, lat = build_meaning_state()
        self.assertIn("не знаю", answer_question(state, lat, "какого цвета окно?").lower())


if __name__ == "__main__":
    unittest.main()
