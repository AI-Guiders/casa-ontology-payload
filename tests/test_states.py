#!/usr/bin/env python3
"""Predicative states — «файл открыт» / «the file is open» → has_state(file, open).

Mirrors the predicative-colour machinery: a one-place predicate as a relation to a state
concept, language-independent, with polarity for negation. Includes the EN copula and the
«open» verb/adjective clash (a state only after a copula).
"""

from __future__ import annotations

import unittest

from casa.curriculum.concept_net import validate
from casa.curriculum.parse import parse_triples
from casa.curriculum.roundtrip import translate_through_meaning
from casa.curriculum.world import build_meaning_state


class StateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state, cls.lat = build_meaning_state()

    def triples(self, text: str) -> list:
        return parse_triples(self.state, self.lat, text)

    def test_predicative_state_both_languages_same_edge(self) -> None:
        edge = [("has_state", "concept.file", "concept.open")]
        self.assertEqual(self.triples("файл открыт"), edge)
        self.assertEqual(self.triples("the file is open"), edge)

    def test_state_validation_needs_a_stateful_thing(self) -> None:
        ok = lambda x, y: validate(self.state, self.lat, "has_state", x, y)["valid"]  # noqa: E731
        self.assertTrue(ok("concept.file", "concept.open"))      # a file is stateful
        self.assertTrue(ok("concept.button", "concept.active"))  # a button is stateful
        self.assertFalse(ok("concept.idea", "concept.open"))     # an idea is not stateful

    def test_state_round_trip_with_gender_agreement(self) -> None:
        # masc / fem / neut short-form predicatives agree with the noun
        self.assertEqual(translate_through_meaning(self.state, self.lat, "файл открыт"),
                         {"ru": "Файл открыт.", "en": "The file is open."})
        self.assertEqual(translate_through_meaning(self.state, self.lat, "the button is active")["ru"],
                         "Кнопка активна.")
        self.assertEqual(translate_through_meaning(self.state, self.lat, "окно скрыто")["en"],
                         "The window is hidden.")

    def test_state_negation(self) -> None:
        self.assertEqual(self.triples("файл не открыт"), self.triples("the file is not open"))
        tr = translate_through_meaning(self.state, self.lat, "файл не открыт")
        self.assertEqual(tr["ru"], "Файл не открыт.")
        self.assertEqual(tr["en"], "The file is not open.")

    def test_open_is_a_verb_without_a_copula(self) -> None:
        # «open the file» must stay the imperative, NOT a predicative state
        self.assertEqual(self.triples("open the file"), [("open", "concept.you", "concept.file")])

    def test_copula_does_not_break_a_locative(self) -> None:
        self.assertEqual(self.triples("the apple is on the table"), [("on", "concept.apple", "concept.table")])


if __name__ == "__main__":
    unittest.main()
