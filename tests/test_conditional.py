#!/usr/bin/env python3
"""Conditional rules «если X, то Y» / «if X then Y» and checking facts against them.

parse_rule turns a conditional into an antecedent + consequent graph; check_against_rules
flags a VIOLATION when the facts establish the antecedent yet contradict the consequent —
the deterministic «rules + facts → violations» guardrail, cross-lingual.
"""

from __future__ import annotations

import unittest

from casa.curriculum.parse import parse_rule
from casa.curriculum.reasoning import check_against_rules
from casa.curriculum.world import build_meaning_state

RULE = "если файл открыт, то кнопка активна"


class ConditionalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.state, cls.lat = build_meaning_state()

    def status(self, facts: list[str], rules: list[str]) -> str:
        return check_against_rules(self.state, self.lat, facts, rules)["results"][0]["status"]

    # --- parse_rule --------------------------------------------------------------------
    def test_parse_rule_states(self) -> None:
        rule = parse_rule(self.state, self.lat, RULE)
        self.assertIsNotNone(rule)
        ante = [(e["rel"], e["src"], e["dst"]) for e in rule["antecedent"]["edges"] if e["satisfied"]]
        cons = [(e["rel"], e["src"], e["dst"]) for e in rule["consequent"]["edges"] if e["satisfied"]]
        self.assertEqual(ante, [("has_state", "concept.file", "concept.open")])
        self.assertEqual(cons, [("has_state", "concept.button", "concept.active")])

    def test_parse_rule_english_then(self) -> None:
        rule = parse_rule(self.state, self.lat, "if the file is open then the button is active")
        self.assertIsNotNone(rule)
        ante = [(e["rel"], e["src"], e["dst"]) for e in rule["antecedent"]["edges"] if e["satisfied"]]
        self.assertEqual(ante, [("has_state", "concept.file", "concept.open")])

    def test_non_conditional_is_not_a_rule(self) -> None:
        self.assertIsNone(parse_rule(self.state, self.lat, "просто фраза без условия"))

    # --- checking facts against rules --------------------------------------------------
    def test_violation_via_state_mutex(self) -> None:
        self.assertEqual(self.status(["файл открыт", "кнопка неактивна"], [RULE]), "violated")

    def test_violation_via_polarity(self) -> None:
        self.assertEqual(self.status(["файл открыт", "кнопка не активна"], [RULE]), "violated")

    def test_satisfied(self) -> None:
        self.assertEqual(self.status(["файл открыт", "кнопка активна"], [RULE]), "satisfied")

    def test_inactive_when_antecedent_absent(self) -> None:
        self.assertEqual(self.status(["кнопка неактивна"], [RULE]), "inactive")

    def test_fired_unknown_when_consequent_unstated(self) -> None:
        self.assertEqual(self.status(["файл открыт"], [RULE]), "fired_unknown")

    def test_cross_lingual_violation(self) -> None:
        # facts in EN + a RU rule -> still a deterministic violation (language-independent graph)
        res = check_against_rules(self.state, self.lat, ["the file is open", "кнопка неактивна"], [RULE])
        self.assertFalse(res["consistent"])
        self.assertEqual(len(res["violations"]), 1)

    def test_unparsed_fact_reported_not_assumed(self) -> None:
        res = check_against_rules(self.state, self.lat, ["файл открыт", "qwzx бессмыслица"], [RULE])
        self.assertEqual([u["text"] for u in res["unparsed_facts"]], ["qwzx бессмыслица"])


if __name__ == "__main__":
    unittest.main()
