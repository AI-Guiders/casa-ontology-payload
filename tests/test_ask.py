#!/usr/bin/env python3
"""Questions to the conceptual network — a query is a partial graph with a variable."""

from __future__ import annotations

import unittest

from casa.curriculum.ask import answer_question, looks_question
from casa.curriculum.parse import parse_graph
from casa.curriculum.situation_store import persist_situation
from casa.curriculum.world import build_meaning_state


class AskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state, cls.lat = build_meaning_state()
        for text in ("яблоко на столе", "книга на столе", "яблоко у окна"):
            persist_situation(cls.state, cls.lat, parse_graph(cls.state, cls.lat, text), label=text)

    def ask(self, q: str) -> str | None:
        return answer_question(self.state, self.lat, q)

    def test_looks_question(self) -> None:
        self.assertTrue(looks_question("что на столе?"))
        self.assertTrue(looks_question("съедобно ли яблоко?"))
        self.assertFalse(looks_question("яблоко на столе"))

    def test_what_is_at_a_ground_lists_remembered_figures(self) -> None:
        a = self.ask("что на столе?")
        self.assertIn("яблоко", a)
        self.assertIn("книга", a)
        self.assertTrue(a.startswith("На столе"))  # preposition + prepositional case

    def test_unknown_ground_is_answered_honestly(self) -> None:
        self.assertIn("ничего не помню", self.ask("что на полу?"))

    def test_where_is_a_figure_gives_a_location(self) -> None:
        a = self.ask("где книга?")
        self.assertIn("книга", a.lower())
        self.assertIn("на столе", a)

    def test_affordance_yes_from_type(self) -> None:
        self.assertTrue(self.ask("съедобно ли яблоко?").startswith("Да"))
        self.assertTrue(self.ask("можно ли пить воду?").startswith("Да"))

    def test_affordance_no_from_type(self) -> None:
        self.assertTrue(self.ask("можно ли есть камень?").startswith("Нет"))
        self.assertTrue(self.ask("съедобна ли книга?").startswith("Нет"))

    def test_material_question_is_honest_when_unknown(self) -> None:
        # nothing was said about the table's material -> honest "не знаю"
        self.assertIn("не знаю", self.ask("из чего стол?").lower())

    def test_material_recalled_after_being_stated(self) -> None:
        from casa.curriculum.converse import answer_clause

        answer_clause(self.state, self.lat, "чашка сделана из стекла")
        a = self.ask("из чего чашка?")
        self.assertIn("чашка", a.lower())
        self.assertIn("стекла", a)  # material in the genitive

    def test_non_question_returns_none(self) -> None:
        self.assertIsNone(self.ask("просто фраза без смысла тут"))


if __name__ == "__main__":
    unittest.main()
