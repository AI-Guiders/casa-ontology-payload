#!/usr/bin/env python3
"""Built-In concept teach on agent-concept-graph."""

from __future__ import annotations

import json
import unittest

from casa._paths import REPO_ROOT
from casa.curriculum.concept_net import affordances_of, isa_closure
from casa.prisms.memory.agent_prism import agent_lattices, ensure_agent_prism
from casa.prisms.memory.concept_built_in import (
    CONCEPT_GRAPH_LATTICE,
    built_in_concept_of,
    built_in_validate,
    ensure_concept_built_in,
    graph_is_populated,
    lemma_en_id,
    lemma_ru_id,
)
from casa.prisms.memory.concept_layer import lex_for_locale, spawn_concept_layer
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.zone import spawn_memory_zone


class ConceptBuiltInTests(unittest.TestCase):
    def _state(self) -> dict:
        state = ensure_prisms({"field_version": 0})
        ensure_agent_prism(state)
        spawn_memory_zone(state)
        return state

    def test_lemma_ids_in_species_scaffold(self) -> None:
        state = self._state()
        spawn_concept_layer(state)
        self.assertEqual(lex_for_locale("concept.orange", "ru"), lemma_ru_id("апельсин"))
        self.assertEqual(lex_for_locale("concept.orange", "en"), lemma_en_id("orange"))

    def test_ensure_concept_built_in_base(self) -> None:
        state = self._state()
        rep = ensure_concept_built_in(state, profile="base", force=True)
        self.assertFalse(rep.get("skipped"))
        self.assertTrue(graph_is_populated(state))
        self.assertIn(CONCEPT_GRAPH_LATTICE, agent_lattices(state))
        self.assertGreaterEqual(rep["concept_count"], 250)
        self.assertTrue(rep["honesty"]["gate_pass"])

    def test_built_in_validate_apple_on_table(self) -> None:
        state = self._state()
        ensure_concept_built_in(state, profile="base", force=True)
        hub_apple = built_in_concept_of(state, "яблоко")
        hub_table = built_in_concept_of(state, "стол")
        self.assertTrue(str(hub_apple or "").startswith("concept."))
        self.assertTrue(str(hub_table or "").startswith("concept."))
        v = built_in_validate(state, "on", "яблоко", "стол")
        self.assertTrue(v["valid"])
        self.assertIn("food", isa_closure(state, CONCEPT_GRAPH_LATTICE, hub_apple))
        self.assertIn("edible", affordances_of(state, CONCEPT_GRAPH_LATTICE, hub_apple))

    def test_idempotent_skip(self) -> None:
        state = self._state()
        first = ensure_concept_built_in(state, profile="base", force=True)
        second = ensure_concept_built_in(state, profile="base", force=False)
        self.assertFalse(first.get("skipped"))
        self.assertTrue(second.get("skipped"))


if __name__ == "__main__":
    unittest.main()
