#!/usr/bin/env python3
"""Textual meaning-graph render — the demo's visible middle layer."""

from __future__ import annotations

import unittest

from casa.curriculum.parse import parse_graph
from casa.curriculum.render import render_graph, render_round_trip
from casa.curriculum.roundtrip import realize_graph
from casa.curriculum.world import build_meaning_state


class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state, cls.lat = build_meaning_state()

    def _graph(self, text: str) -> dict:
        return parse_graph(self.state, self.lat, text)

    def test_valid_chain_renders_inline_with_legend(self) -> None:
        block = render_graph(self._graph("яблоко на столе у окна"))
        # language-independent concept leaves, not surface words
        self.assertIn("apple", block)
        self.assertIn("table", block)
        self.assertIn("window", block)
        # relations appear on the edge chain
        self.assertIn("on", block)
        self.assertIn("near", block)
        # legend shows a distinguishing type and hides the generic physical_object
        self.assertIn("fruit", block)
        self.assertNotIn("physical_object", block)
        # a clean situation has no failure marker
        self.assertNotIn("✗", block)

    def test_category_error_marks_unsatisfied_edge(self) -> None:
        block = render_graph(self._graph("стол ест яблоко"))
        self.assertIn("✗", block)
        self.assertIn("eat", block)
        self.assertIn("agent", block)  # the missing role is named

    def test_same_graph_from_both_languages(self) -> None:
        # the claim the demo makes: RU and EN inputs yield the identical graph block
        ru_block = render_graph(self._graph("яблоко на столе"))
        en_block = render_graph(self._graph("The apple is on the table"))
        self.assertEqual(ru_block, en_block)

    def test_round_trip_block_has_both_realizations_and_note(self) -> None:
        g = self._graph("кот пьёт молоко")
        ru = realize_graph(self.state, self.lat, g, lang="ru")
        en = realize_graph(self.state, self.lat, g, lang="en")
        block = render_round_trip(g, source="кот пьёт молоко", ru=ru, en=en)
        self.assertIn("вход: «кот пьёт молоко»", block)
        self.assertIn("→ RU: Кот пьёт молоко.", block)
        self.assertIn("→ EN: The cat drinks the milk.", block)
        self.assertIn("смысл, не слова", block)


if __name__ == "__main__":
    unittest.main()
