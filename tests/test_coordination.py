#!/usr/bin/env python3
"""Coordination with «и»/«and» — a role (figure / object / clause) distributes over conjuncts."""

from __future__ import annotations

import unittest

from casa.curriculum.parse import parse_graph, parse_triples
from casa.curriculum.roundtrip import translate_through_meaning
from casa.curriculum.situation import fingerprint
from casa.curriculum.world import build_meaning_state


class CoordinationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state, cls.lat = build_meaning_state()

    def rt(self, text: str) -> dict:
        return translate_through_meaning(self.state, self.lat, text)

    def test_coordinated_clauses(self) -> None:
        self.assertEqual(parse_triples(self.state, self.lat, "открой файл и сохрани документ"),
                         [("open", "concept.you", "concept.file"), ("save", "concept.you", "concept.document")])
        tr = self.rt("открой файл и сохрани документ")
        self.assertEqual(tr["ru"], "Открой файл и сохрани документ.")
        self.assertEqual(tr["en"], "Open the file and save the document.")

    def test_coordinated_objects_factor_the_verb(self) -> None:
        tr = self.rt("удали файл и папку")
        self.assertEqual(tr["ru"], "Удали файл и папку.")
        self.assertEqual(tr["en"], "Delete the file and the folder.")

    def test_coordinated_figures_factor_the_location(self) -> None:
        tr = self.rt("яблоко и книга на столе")
        self.assertEqual(tr["ru"], "Яблоко и книга на столе.")
        self.assertEqual(tr["en"], "The apple and the book are on the table.")  # plural «are»

    def test_shared_subject_several_predicates(self) -> None:
        tr = self.rt("собака ест мясо и пьёт молоко")
        self.assertEqual(tr["ru"], "Собака ест мясо и пьёт молоко.")          # subject once
        self.assertEqual(tr["en"], "The dog eats the meat and drinks the milk.")

    def test_cross_lingual(self) -> None:
        self.assertEqual(self.rt("open the file and save the document")["ru"],
                         "Открой файл и сохрани документ.")

    def test_coordination_changes_the_fingerprint(self) -> None:
        one = fingerprint(parse_graph(self.state, self.lat, "удали файл"))["id"]
        two = fingerprint(parse_graph(self.state, self.lat, "удали файл и папку"))["id"]
        self.assertNotEqual(one, two)  # «file and folder» is a distinct situation from «file»

    def test_nested_locative_is_not_coordination(self) -> None:
        # «яблоко на столе у окна» is one chained clause, not coordinated
        tr = self.rt("яблоко на столе у окна")
        self.assertEqual(tr["ru"], "Яблоко на столе у окна.")
        self.assertEqual(tr["en"], "The apple is on the table near the window.")


if __name__ == "__main__":
    unittest.main()
