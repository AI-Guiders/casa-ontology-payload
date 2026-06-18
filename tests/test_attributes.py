#!/usr/bin/env python3
"""Adjective attributes — modifiers ride on concept nodes and agree in Russian."""

from __future__ import annotations

import unittest

from casa.curriculum.attributes import attr_of_token, ru_adjective
from casa.curriculum.parse import parse_graph, parse_situation
from casa.curriculum.roundtrip import realize_graph
from casa.curriculum.world import build_meaning_state


class AttributeLexiconTests(unittest.TestCase):
    def test_surface_resolves_either_language(self) -> None:
        self.assertEqual(attr_of_token("красное"), "red")
        self.assertEqual(attr_of_token("красная"), "red")
        self.assertEqual(attr_of_token("red"), "red")
        self.assertIsNone(attr_of_token("яблоко"))

    def test_russian_agreement_by_noun_gender(self) -> None:
        self.assertEqual(ru_adjective("red", "яблоко"), "красное")   # neuter
        self.assertEqual(ru_adjective("red", "стол"), "красный")     # masc (consonant)
        self.assertEqual(ru_adjective("red", "книга"), "красная")    # feminine


class AttributeRoundTripTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state, cls.lat = build_meaning_state()

    def test_adjective_binds_to_its_noun_in_the_graph(self) -> None:
        triples, attrs, _polarity = parse_situation(self.state, self.lat, "красное яблоко на столе")
        self.assertEqual(triples, [("on", "lex.apple", "lex.table")])
        self.assertEqual(attrs.get("lex.apple"), ["red"])
        self.assertNotIn("lex.table", attrs)  # the adjective binds to apple, not table

    def test_locative_figure_agrees_and_translates(self) -> None:
        g = parse_graph(self.state, self.lat, "красное яблоко на столе")
        self.assertEqual(g["nodes"]["lex.apple"].get("attrs"), ["red"])
        self.assertEqual(realize_graph(self.state, self.lat, g, lang="ru"), "Красное яблоко на столе.")
        self.assertEqual(realize_graph(self.state, self.lat, g, lang="en"), "The red apple is on the table.")

    def test_transitive_subject_takes_the_adjective(self) -> None:
        g = parse_graph(self.state, self.lat, "большая собака ест мясо")
        self.assertEqual(realize_graph(self.state, self.lat, g, lang="ru"), "Большая собака ест мясо.")
        self.assertEqual(realize_graph(self.state, self.lat, g, lang="en"), "The big dog eats the meat.")

    def test_same_graph_from_both_languages_with_adjective(self) -> None:
        ru = parse_graph(self.state, self.lat, "красное яблоко на столе")
        en = parse_graph(self.state, self.lat, "red apple on the table")
        self.assertEqual(ru["nodes"]["lex.apple"].get("attrs"), en["nodes"]["lex.apple"].get("attrs"))
        # the English input still round-trips into agreed Russian
        self.assertEqual(realize_graph(self.state, self.lat, en, lang="ru"), "Красное яблоко на столе.")


if __name__ == "__main__":
    unittest.main()
