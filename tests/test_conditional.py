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

    # --- multi-condition rules «если X и Y, то Z» --------------------------------------
    def test_multi_condition_antecedent_parses_all(self) -> None:
        rule = parse_rule(self.state, self.lat, "если файл открыт и кнопка активна, то окно видно")
        ante = {(e["rel"], e["src"], e["dst"]) for e in rule["antecedent"]["edges"] if e["satisfied"]}
        self.assertEqual(ante, {("has_state", "concept.file", "concept.open"),
                                ("has_state", "concept.button", "concept.active")})

    def test_multi_condition_mixes_forms(self) -> None:
        # a state AND a locative — impossible in a single clause parse, works as a conjunction
        rule = parse_rule(self.state, self.lat, "если файл открыт и яблоко на столе, то окно видно")
        ante = {(e["rel"], e["src"], e["dst"]) for e in rule["antecedent"]["edges"] if e["satisfied"]}
        self.assertEqual(ante, {("has_state", "concept.file", "concept.open"),
                                ("on", "concept.apple", "concept.table")})

    def test_intra_clause_coordination_is_not_split(self) -> None:
        # «яблоко и книга на столе» is ONE clause (two figures), not two conditions
        rule = parse_rule(self.state, self.lat, "если яблоко и книга на столе, то окно видно")
        ante = {(e["rel"], e["src"], e["dst"]) for e in rule["antecedent"]["edges"] if e["satisfied"]}
        self.assertEqual(ante, {("on", "concept.apple", "concept.table"),
                                ("on", "concept.book", "concept.table")})

    MULTI = "если файл открыт и кнопка активна, то окно видно"

    def test_multi_condition_fires_only_when_all_hold(self) -> None:
        # only one condition present -> antecedent not established -> inactive
        self.assertEqual(self.status(["файл открыт", "окно скрыто"], [self.MULTI]), "inactive")

    def test_multi_condition_violation_when_all_hold(self) -> None:
        # both conditions hold and the consequent is contradicted -> violated
        self.assertEqual(self.status(["файл открыт", "кнопка активна", "окно скрыто"], [self.MULTI]), "violated")

    def test_multi_condition_satisfied(self) -> None:
        self.assertEqual(self.status(["файл открыт", "кнопка активна", "окно видно"], [self.MULTI]), "satisfied")

    # --- threshold matching in a rule ANTECEDENT («=15» satisfies «больше 10») ---------
    THRESH = "если воды больше 10 мл, то панель видна"

    def test_threshold_antecedent_fires_when_value_crosses(self) -> None:
        self.assertEqual(self.status(["воды равно 15 мл"], [self.THRESH]), "fired_unknown")
        self.assertEqual(self.status(["воды равно 15 мл", "панель скрыта"], [self.THRESH]), "violated")
        self.assertEqual(self.status(["воды равно 15 мл", "панель видна"], [self.THRESH]), "satisfied")

    def test_threshold_antecedent_inactive_below(self) -> None:
        self.assertEqual(self.status(["воды равно 5 мл"], [self.THRESH]), "inactive")  # 5 is not > 10

    def test_threshold_antecedent_inequality_entails(self) -> None:
        self.assertEqual(self.status(["воды больше 12 мл"], [self.THRESH]), "fired_unknown")  # >12 ⊆ >10

    def test_threshold_antecedent_unit_mismatch_inactive(self) -> None:
        self.assertEqual(self.status(["воды равно 15 мг"], [self.THRESH]), "inactive")  # mg vs ml


if __name__ == "__main__":
    unittest.main()
