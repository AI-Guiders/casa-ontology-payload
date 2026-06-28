#!/usr/bin/env python3
"""Forward-chaining — derive new facts from rules, catch contradictions several steps ahead.

The value over the one-shot check: «A», «если A то B», «если B то C», «не C» is consistent
to the direct check (B and C are never given), but forward-chaining derives B then C and
finds C clashing with ¬C two hops in.
"""

from __future__ import annotations

import unittest

from casa.curriculum.reasoning import check_against_rules, forward_chain
from casa.curriculum.world import build_meaning_state

# A -> B -> C  («файл открыт» derives «окно видно» derives «кнопка активна»)
CHAIN = ["если файл открыт, то окно видно", "если окно видно, то кнопка активна"]


class ForwardChainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state, cls.lat = build_meaning_state()

    def test_consistent_chain_derives_transitive_facts(self) -> None:
        res = forward_chain(self.state, self.lat, ["файл открыт"], CHAIN)
        self.assertTrue(res["consistent"])
        derived = {d["edge"] for d in res["derived_facts"]}
        self.assertIn("has_state(concept.window,concept.visible)", derived)
        self.assertIn("has_state(concept.button,concept.active)", derived)

    def test_derived_violation_two_steps(self) -> None:
        res = forward_chain(self.state, self.lat, ["файл открыт", "кнопка неактивна"], CHAIN)
        self.assertFalse(res["consistent"])
        self.assertEqual(len(res["violations"]), 1)
        self.assertTrue(res["violations"][0]["chained"])  # found via a derived fact, not given

    def test_forward_chain_beats_direct_check(self) -> None:
        # the SAME input: the one-shot check sees no violation, forward-chaining does
        facts = ["файл открыт", "кнопка неактивна"]
        self.assertTrue(check_against_rules(self.state, self.lat, facts, CHAIN)["consistent"])
        self.assertFalse(forward_chain(self.state, self.lat, facts, CHAIN)["consistent"])

    def test_direct_violation_is_not_flagged_chained(self) -> None:
        res = forward_chain(self.state, self.lat, ["файл открыт", "кнопка неактивна"],
                            ["если файл открыт, то кнопка активна"])
        self.assertFalse(res["consistent"])
        self.assertFalse(res["violations"][0]["chained"])  # explainable by given facts alone

    def test_reaches_fixpoint(self) -> None:
        # a derivable chain terminates with a bounded number of steps
        res = forward_chain(self.state, self.lat, ["файл открыт"], CHAIN)
        self.assertLessEqual(res["steps"], 32)
        self.assertGreaterEqual(len(res["derived_facts"]), 2)

    def test_unparsed_fact_reported(self) -> None:
        res = forward_chain(self.state, self.lat, ["файл открыт", "qwzx бессмыслица"], CHAIN)
        self.assertEqual([u["text"] for u in res["unparsed_facts"]], ["qwzx бессмыслица"])


if __name__ == "__main__":
    unittest.main()
