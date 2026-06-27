#!/usr/bin/env python3
"""lives_in — habitat relation: «кошка живёт в доме» / «где живёт кошка?»."""

from __future__ import annotations

import unittest

from casa.curriculum.ask import answer_question
from casa.curriculum.converse import answer_clause
from casa.curriculum.parse import parse_graph, parse_triples
from casa.curriculum.roundtrip import translate_through_meaning
from casa.curriculum.world import build_meaning_state


class HabitatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state, cls.lat = build_meaning_state()

    def test_statement_absorbs_the_preposition(self) -> None:
        # one lives_in edge, not action+location — a home is a habitat, not a container
        self.assertEqual(parse_triples(self.state, self.lat, "кошка живёт в доме"),
                         [("lives_in", "concept.cat", "concept.house")])

    def test_round_trip(self) -> None:
        tr = translate_through_meaning(self.state, self.lat, "кошка живёт в доме")
        self.assertEqual(tr["ru"], "Кот живёт в доме.")          # «в» + prepositional case
        self.assertEqual(tr["en"], "The cat lives in the house.")
        self.assertEqual(translate_through_meaning(self.state, self.lat, "the cat lives in the house")["ru"],
                         "Кот живёт в доме.")

    def test_non_animate_is_refused(self) -> None:
        g = parse_graph(self.state, self.lat, "идея живёт в доме")  # an idea does not live
        self.assertFalse(any(e["satisfied"] for e in g["edges"]))

    def test_habitat_question(self) -> None:
        state, lat = build_meaning_state()
        answer_clause(state, lat, "кошка живёт в доме")
        self.assertEqual(answer_question(state, lat, "где живёт кошка?"), "Кот живёт в доме.")


if __name__ == "__main__":
    unittest.main()
