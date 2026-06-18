#!/usr/bin/env python3
"""Negation / polarity (B5) — «не закрывай окно» is a distinct situation from «закрой окно».

Polarity rides on the edge and enters the fingerprint, so a negated situation never
collides with its positive — the kernel a cross-lingual / grounding validator needs
(a dropped «не» is the most dangerous mistranslation)."""

from __future__ import annotations

import unittest

from casa.curriculum.parse import parse_graph
from casa.curriculum.roundtrip import translate_through_meaning
from casa.curriculum.situation import canonical_edges, fingerprint
from casa.curriculum.world import build_meaning_state


class NegationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state, cls.lat = build_meaning_state()

    def rt(self, text: str) -> dict:
        return translate_through_meaning(self.state, self.lat, text)

    def test_negative_imperative_round_trip(self) -> None:
        tr = self.rt("не закрывай окно")
        self.assertEqual(tr["ru"], "Не закрывай окно.")        # imperfective imperative
        self.assertEqual(tr["en"], "Do not close the window.")

    def test_negative_imperative_from_english(self) -> None:
        tr = self.rt("Do not delete the file")
        self.assertEqual(tr["ru"], "Не удаляй файл.")
        self.assertEqual(tr["en"], "Do not delete the file.")

    def test_negative_declarative_uses_do_support(self) -> None:
        tr = self.rt("пользователь не открывает файл")
        self.assertEqual(tr["ru"], "Пользователь не открывает файл.")
        self.assertEqual(tr["en"], "The user does not open the file.")

    def test_polarity_is_in_the_fingerprint(self) -> None:
        pos = fingerprint(parse_graph(self.state, self.lat, "пользователь открывает файл"))["id"]
        neg = fingerprint(parse_graph(self.state, self.lat, "пользователь не открывает файл"))["id"]
        self.assertNotEqual(pos, neg)  # a dropped «не» changes the situation id

    def test_negated_edge_key_carries_the_marker(self) -> None:
        g = parse_graph(self.state, self.lat, "не удаляй файл")
        self.assertTrue(any(k.startswith("¬") for k in canonical_edges(g)))

    def test_positive_clause_is_unaffected(self) -> None:
        tr = self.rt("открой файл")
        self.assertEqual(tr["ru"], "Открой файл.")
        self.assertEqual(tr["en"], "Open the file.")
        g = parse_graph(self.state, self.lat, "открой файл")
        self.assertFalse(any(k.startswith("¬") for k in canonical_edges(g)))


if __name__ == "__main__":
    unittest.main()
