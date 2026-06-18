#!/usr/bin/env python3
"""Software / UI domain layer — concepts, action verbs, validation, round-trip."""

from __future__ import annotations

import unittest

from casa.curriculum.concept_net import affordances_of, concept_of, validate
from casa.curriculum.roundtrip import translate_through_meaning
from casa.curriculum.world import build_meaning_state


class SoftwareDomainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state, cls.lat = build_meaning_state()

    def afford(self, word: str) -> set[str]:
        return affordances_of(self.state, self.lat, concept_of(self.state, self.lat, word))

    def test_software_concepts_carry_their_affordances(self) -> None:
        self.assertEqual(concept_of(self.state, self.lat, "файл"), "lex.file")
        self.assertIn("openable", self.afford("файл"))
        self.assertIn("savable", self.afford("файл"))
        self.assertIn("clickable", self.afford("кнопка"))
        self.assertNotIn("savable", self.afford("кнопка"))  # a button is not savable
        self.assertIn("agent", self.afford("пользователь"))

    def test_action_validation(self) -> None:
        ok = lambda r, y: validate(self.state, self.lat, r, "пользователь", y)["valid"]
        self.assertTrue(ok("open", "файл"))
        self.assertTrue(ok("delete", "папка"))
        self.assertTrue(ok("click", "кнопка"))
        self.assertFalse(ok("save", "кнопка"))   # button is not savable
        self.assertFalse(ok("click", "файл"))    # a file is not clickable

    def test_declarative_round_trip_both_languages(self) -> None:
        tr = translate_through_meaning(self.state, self.lat, "пользователь открывает файл")
        self.assertEqual(tr["ru"], "Пользователь открывает файл.")
        self.assertEqual(tr["en"], "The user opens the file.")

    def test_accusative_object_declension(self) -> None:
        tr = translate_through_meaning(self.state, self.lat, "пользователь удаляет папку")
        self.assertEqual(tr["ru"], "Пользователь удаляет папку.")  # папка -> папку

    def test_english_input_round_trips_to_russian(self) -> None:
        tr = translate_through_meaning(self.state, self.lat, "The user saves the document")
        self.assertEqual(tr["ru"], "Пользователь сохраняет документ.")

    def test_imperative_round_trip(self) -> None:
        tr = translate_through_meaning(self.state, self.lat, "открой файл")
        self.assertEqual(tr["ru"], "Открой файл.")
        self.assertEqual(tr["en"], "Open the file.")
        # accusative on a feminine object
        self.assertEqual(translate_through_meaning(self.state, self.lat, "удали папку")["ru"], "Удали папку.")

    def test_imperative_from_english(self) -> None:
        tr = translate_through_meaning(self.state, self.lat, "Save the document")
        self.assertEqual(tr["ru"], "Сохрани документ.")

    def test_noun_before_verb_is_not_an_imperative(self) -> None:
        from casa.curriculum.parse import parse_triples

        # «собака ест» (subject-verb) must NOT be read as a command «eat the dog»
        self.assertEqual(parse_triples(self.state, self.lat, "собака ест"), [])


if __name__ == "__main__":
    unittest.main()
