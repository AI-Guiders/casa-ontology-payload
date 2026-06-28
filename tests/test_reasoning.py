#!/usr/bin/env python3
"""Reasoning over situations — deterministic consistency checking (relate / check_consistency).

The logic question «can two statements be true together?», built on the same language-
independent fingerprint as the equivalence validator. Contradiction reuses the dangerous
kernel (polarity / quantity / unit) + functional relations; entailment is exact edge-set
containment.
"""

from __future__ import annotations

import unittest

from casa.curriculum.reasoning import check_consistency, relate
from casa.curriculum.world import build_meaning_state


class ReasoningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state, cls.lat = build_meaning_state()

    def verdict(self, a: str, b: str) -> str:
        return relate(self.state, self.lat, a, b)["verdict"]

    def classes(self, a: str, b: str) -> set[str]:
        return {c["class"] for c in relate(self.state, self.lat, a, b)["conflicts"]}

    # --- contradiction: the dangerous kernel, within one language and cross-lingual ----
    def test_polarity_contradiction(self) -> None:
        self.assertEqual(self.verdict("яблоко на столе", "яблоко не на столе"), "contradicts")
        self.assertIn("polarity", self.classes("яблоко на столе", "яблоко не на столе"))

    def test_polarity_contradiction_cross_lingual(self) -> None:
        # the whole point: the graph is language-independent, so the contradiction is too
        self.assertEqual(self.verdict("open the file", "не открывай файл"), "contradicts")
        self.assertIn("polarity", self.classes("open the file", "не открывай файл"))

    def test_quantity_contradiction(self) -> None:
        self.assertEqual(self.verdict("удали два файла", "удали три файла"), "contradicts")
        self.assertIn("quantity", self.classes("удали два файла", "удали три файла"))

    def test_unit_contradiction(self) -> None:
        self.assertEqual(self.verdict("5 мл воды на столе", "5 мг воды на столе"), "contradicts")
        self.assertIn("unit", self.classes("5 мл воды на столе", "5 мг воды на столе"))

    def test_functional_colour_contradiction(self) -> None:
        # colour is one-per-thing: red vs blue is a contradiction, not two independent facts
        self.assertEqual(self.verdict("яблоко красное", "яблоко синее"), "contradicts")
        self.assertIn("functional", self.classes("яблоко красное", "яблоко синее"))

    # --- entailment / equivalence / independence --------------------------------------
    def test_entailment_directions(self) -> None:
        self.assertEqual(self.verdict("яблоко на столе у окна", "яблоко на столе"), "entails")
        self.assertEqual(self.verdict("яблоко на столе", "яблоко на столе у окна"), "entailed_by")

    def test_equivalent_cross_lingual(self) -> None:
        self.assertEqual(self.verdict("яблоко на столе", "apple on the table"), "equivalent")

    def test_independent(self) -> None:
        # same relation+ground, different figure, no containment, no conflict
        self.assertEqual(self.verdict("яблоко на столе", "книга на столе"), "independent")

    def test_unknown_when_a_side_does_not_parse(self) -> None:
        # integrity: never assert a relation when a side did not parse to a situation
        self.assertEqual(self.verdict("яблоко на столе", "kiconedit configuration dialog"), "unknown")

    def test_more_specific_is_not_a_contradiction(self) -> None:
        # a nested locative entails the bare one — it must NOT be read as a contradiction
        self.assertNotEqual(self.verdict("яблоко на столе у окна", "яблоко на столе"), "contradicts")

    # --- set-level consistency ---------------------------------------------------------
    def test_check_consistency_flags_pairs_and_excludes_unparsed(self) -> None:
        res = check_consistency(self.state, self.lat, [
            "яблоко на столе",         # 0
            "яблоко не на столе",      # 1  -> contradicts 0 (polarity)
            "удали два файла",         # 2
            "удали три файла",         # 3  -> contradicts 2 (quantity)
            "qwzx nonsense",           # 4  -> unparsed, excluded
        ])
        self.assertFalse(res["consistent"])
        self.assertEqual(len(res["contradictions"]), 2)
        pairs = {(c["a_index"], c["b_index"]) for c in res["contradictions"]}
        self.assertEqual(pairs, {(0, 1), (2, 3)})
        self.assertEqual([u["index"] for u in res["unparsed"]], [4])

    def test_check_consistency_clean_set(self) -> None:
        res = check_consistency(self.state, self.lat,
                                ["яблоко на столе", "книга на столе", "open the file"])
        self.assertTrue(res["consistent"])
        self.assertEqual(res["contradictions"], [])
        self.assertEqual(res["checked"], 3)

    def test_curated_demo_renders(self) -> None:
        from casa.curriculum.demo_reason import render_reason_demo

        text = render_reason_demo(self.state, self.lat)
        self.assertIn("СЛОЙ РАССУЖДЕНИЯ", text)   # header present
        self.assertIn("ПРОТИВОРЕЧИ", text)         # at least one contradiction shown
        self.assertIn("следует", text)             # at least one entailment shown


if __name__ == "__main__":
    unittest.main()
