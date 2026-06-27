#!/usr/bin/env python3
"""Action with a destination — «сохрани файл в папку»: the goal is a real node in the graph."""

from __future__ import annotations

import unittest

from casa.curriculum.parse import parse_graph, parse_triples
from casa.curriculum.roundtrip import translate_through_meaning
from casa.curriculum.situation import fingerprint
from casa.curriculum.world import build_meaning_state


class DestinationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state, cls.lat = build_meaning_state()

    def rt(self, text: str) -> dict:
        return translate_through_meaning(self.state, self.lat, text)

    def test_two_edges_action_plus_destination(self) -> None:
        self.assertEqual(parse_triples(self.state, self.lat, "сохрани файл в папку"),
                         [("save", "concept.you", "concept.file"), ("in", "concept.file", "concept.folder")])

    def test_both_edges_validate(self) -> None:
        g = parse_graph(self.state, self.lat, "сохрани файл в папку")
        self.assertTrue(all(e["satisfied"] for e in g["edges"]))

    def test_round_trip(self) -> None:
        tr = self.rt("сохрани файл в папку")
        self.assertEqual(tr["ru"], "Сохрани файл в папку.")        # «в» + accusative «папку»
        self.assertEqual(tr["en"], "Save the file to the folder.")

    def test_cross_lingual(self) -> None:
        self.assertEqual(self.rt("save the file to the folder")["ru"], "Сохрани файл в папку.")

    def test_declarative_and_negation(self) -> None:
        self.assertEqual(self.rt("пользователь сохраняет файл в папку")["en"],
                         "The user saves the file to the folder.")
        self.assertEqual(self.rt("не сохраняй файл в папку")["en"], "Do not save the file to the folder.")

    def test_destination_is_in_the_fingerprint(self) -> None:
        folder = fingerprint(parse_graph(self.state, self.lat, "сохрани файл в папку"))["id"]
        clip = fingerprint(parse_graph(self.state, self.lat, "сохрани файл в буфер"))["id"]
        bare = fingerprint(parse_graph(self.state, self.lat, "сохрани файл"))["id"]
        self.assertNotEqual(folder, clip)   # «to folder» ≠ «to clipboard» — validator-visible
        self.assertNotEqual(folder, bare)


if __name__ == "__main__":
    unittest.main()
