#!/usr/bin/env python3
"""Quantities (B4) — «два файла»: count on the node, in the fingerprint, in the surface."""

from __future__ import annotations

import unittest

from casa.curriculum.parse import parse_graph
from casa.curriculum.quantity import number_of_token, ru_noun_case, ru_number_word
from casa.curriculum.roundtrip import translate_through_meaning
from casa.curriculum.situation import canonical_edges, fingerprint
from casa.curriculum.world import build_meaning_state


class QuantityLexiconTests(unittest.TestCase):
    def test_number_surfaces(self) -> None:
        self.assertEqual(number_of_token("два"), 2)
        self.assertEqual(number_of_token("две"), 2)
        self.assertEqual(number_of_token("two"), 2)
        self.assertEqual(number_of_token("3"), 3)
        self.assertIsNone(number_of_token("файл"))

    def test_numeral_word_agrees_in_gender_for_two(self) -> None:
        self.assertEqual(ru_number_word(2, "m"), "два")
        self.assertEqual(ru_number_word(2, "f"), "две")

    def test_governed_case(self) -> None:
        self.assertEqual(ru_noun_case(1), "nom")
        self.assertEqual(ru_noun_case(3), "gen")
        self.assertEqual(ru_noun_case(7), "gen-pl")


class QuantityRoundTripTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state, cls.lat = build_meaning_state()

    def rt(self, text: str) -> dict:
        return translate_through_meaning(self.state, self.lat, text)

    def test_count_binds_to_the_noun_in_the_graph(self) -> None:
        g = parse_graph(self.state, self.lat, "удали два файла")
        self.assertEqual(g["nodes"]["concept.file"].get("count"), 2)

    def test_counted_object_imperative(self) -> None:
        tr = self.rt("удали два файла")
        self.assertEqual(tr["ru"], "Удали два файла.")      # genitive singular after 2
        self.assertEqual(tr["en"], "Delete two files.")     # no article, plural noun

    def test_counted_figure_locative(self) -> None:
        tr = self.rt("две книги на столе")
        self.assertEqual(tr["ru"], "Две книги на столе.")   # «две» (feminine)
        self.assertEqual(tr["en"], "Two books are on the table.")

    def test_count_is_in_the_fingerprint(self) -> None:
        two = fingerprint(parse_graph(self.state, self.lat, "удали два файла"))["id"]
        three = fingerprint(parse_graph(self.state, self.lat, "удали три файла"))["id"]
        bare = fingerprint(parse_graph(self.state, self.lat, "удали файл"))["id"]
        self.assertNotEqual(two, three)   # 5↔50-style error is id-visible
        self.assertNotEqual(two, bare)

    def test_count_annotates_the_canonical_edge(self) -> None:
        self.assertIn("delete(concept.you,concept.file×2)", canonical_edges(parse_graph(self.state, self.lat, "удали два файла")))

    def test_english_plural_input_with_count(self) -> None:
        # the English side is first-class: «two files» (plural) resolves and round-trips
        tr = translate_through_meaning(self.state, self.lat, "delete two files")
        self.assertEqual(tr["ru"], "Удали два файла.")
        self.assertEqual(tr["en"], "Delete two files.")

    def test_measure_with_unit_on_the_node(self) -> None:
        g = parse_graph(self.state, self.lat, "5 мл воды на столе")
        self.assertEqual(g["nodes"]["concept.water"].get("measure"), {"value": 5, "unit": "ml"})

    def test_measure_round_trip(self) -> None:
        tr = translate_through_meaning(self.state, self.lat, "5 мл воды на столе")
        self.assertEqual(tr["ru"], "5 мл воды на столе.")
        self.assertEqual(tr["en"], "5 ml of water is on the table.")

    def test_measure_in_fingerprint_distinguishes_unit_and_value(self) -> None:
        ml5 = fingerprint(parse_graph(self.state, self.lat, "5 мл воды на столе"))["id"]
        mg5 = fingerprint(parse_graph(self.state, self.lat, "5 мг воды на столе"))["id"]
        ml50 = fingerprint(parse_graph(self.state, self.lat, "50 мл воды на столе"))["id"]
        self.assertNotEqual(ml5, mg5)   # ml ≠ mg
        self.assertNotEqual(ml5, ml50)  # 5 ≠ 50


if __name__ == "__main__":
    unittest.main()
