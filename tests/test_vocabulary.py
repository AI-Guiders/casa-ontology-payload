#!/usr/bin/env python3
"""Vocabulary widening — more everyday verbs, colours and quality adjectives."""

from __future__ import annotations

import unittest

from casa.curriculum.parse import parse_graph
from casa.curriculum.roundtrip import translate_through_meaning
from casa.curriculum.world import build_meaning_state


class VocabularyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state, cls.lat = build_meaning_state()

    def rt(self, text: str) -> dict:
        return translate_through_meaning(self.state, self.lat, text)

    def test_everyday_verbs_round_trip(self) -> None:
        cases = {
            "мужчина носит рубашку": "The man wears the shirt.",
            "повар использует нож": "The cook uses the knife.",
            "мальчик пишет письмо": "The boy writes the letter.",
            "повар готовит суп": "The cook cooks the soup.",
            "женщина моет тарелку": "The woman washes the plate.",
        }
        for ru, en in cases.items():
            self.assertEqual(self.rt(ru)["en"], en)

    def test_verb_selectional_refusals(self) -> None:
        ok = lambda t: any(e["satisfied"] for e in parse_graph(self.state, self.lat, t)["edges"])
        self.assertFalse(ok("повар готовит нож"))   # a knife is not cookable
        self.assertFalse(ok("мужчина носит суп"))   # soup is not wearable
        self.assertFalse(ok("помой идею"))          # an idea is not washable

    def test_new_colours(self) -> None:
        self.assertEqual(self.rt("синяя книга на столе")["en"], "The blue book is on the table.")
        self.assertEqual(self.rt("книга синяя")["en"], "The book is blue.")  # predicative

    def test_quality_adjectives(self) -> None:
        self.assertEqual(self.rt("горячий суп на столе")["en"], "The hot soup is on the table.")
        self.assertEqual(self.rt("грязная тарелка на столе")["en"], "The dirty plate is on the table.")


if __name__ == "__main__":
    unittest.main()
