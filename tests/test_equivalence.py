#!/usr/bin/env python3
"""Meaning-equivalence triage (the validator spike) — three honest states."""

from __future__ import annotations

import unittest

from casa.curriculum.equivalence import check_equivalence
from casa.curriculum.world import build_meaning_state


class EquivalenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state, cls.lat = build_meaning_state()

    def verdict(self, s: str, t: str) -> dict:
        return check_equivalence(self.state, self.lat, s, t)

    def test_correct_cross_lingual_translation_is_equivalent(self) -> None:
        self.assertEqual(self.verdict("открой файл", "open the file")["verdict"], "equivalent")
        self.assertEqual(self.verdict("яблоко на столе", "The apple is on the table")["verdict"], "equivalent")

    def test_dropped_negation_is_flagged_as_polarity(self) -> None:
        r = self.verdict("не удаляй файл", "delete the file")
        self.assertEqual(r["verdict"], "divergent")
        self.assertEqual(r["divergences"][0]["class"], "polarity")

    def test_wrong_number_is_flagged_as_quantity(self) -> None:
        r = self.verdict("удали два файла", "удали три файла")
        self.assertEqual(r["verdict"], "divergent")
        self.assertTrue(any(d["class"] == "quantity" for d in r["divergences"]))

    def test_unparsable_side_is_uncheckable_never_equivalent(self) -> None:
        r = self.verdict("открой файл", "это просто свободный текст без понятий")
        self.assertEqual(r["verdict"], "uncheckable")
        # integrity: an unparsed side must NEVER be called equivalent
        self.assertNotEqual(r["verdict"], "equivalent")

    def test_both_unparsable_is_uncheckable(self) -> None:
        self.assertEqual(self.verdict("привет как дела", "hello how are you")["verdict"], "uncheckable")

    def test_negation_preserved_is_equivalent(self) -> None:
        # a CORRECT negative translation must pass, not false-flag
        self.assertEqual(self.verdict("не удаляй файл", "do not delete the file")["verdict"], "equivalent")


if __name__ == "__main__":
    unittest.main()
