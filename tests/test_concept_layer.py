#!/usr/bin/env python3
"""Concept layer — hub vs lex split (ADR-0073 P18)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from casa.domain.dialogue_bind.binder import _dedupe_blocks
from casa.domain.dialogue_bind.blocks import block_dict
from casa.prisms.memory.agent_prism import agent_lattices, ensure_agent_prism
from casa.prisms.memory.concept_layer import (
    CONCEPT_CORE_LATTICE,
    bind_concept_id,
    build_concept_honesty_report,
    canonical_concept_id,
    lex_for_locale,
    normalize_bind_blocks,
    spawn_concept_layer,
    spawn_concept_prism,
    write_concept_honesty_artifact,
)
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.zone import ensure_memory_zone, spawn_memory_zone
from casa.prisms.tick.discourse.budget import discourse_budget_from_blocks


class ConceptLayerTests(unittest.TestCase):
    def _state(self) -> dict:
        state = ensure_prisms({"field_version": 0})
        ensure_agent_prism(state)
        spawn_memory_zone(state)
        return state

    def test_canonical_concept_id_maps_legacy_lex(self) -> None:
        self.assertEqual(canonical_concept_id("lang.word.apelsin"), "concept.orange")
        self.assertEqual(canonical_concept_id("lex.en.orange"), "concept.orange")
        self.assertEqual(canonical_concept_id("lang.meta.compare.greater"), "lang.meta.compare.greater")

    def test_bind_concept_id_unifies_ru_en_surfaces(self) -> None:
        self.assertEqual(bind_concept_id("lemma.ru.okno"), "concept.window")
        self.assertEqual(bind_concept_id("lemma.en.window"), "concept.window")
        self.assertEqual(bind_concept_id("lex.ru.okno"), "concept.window")
        self.assertEqual(bind_concept_id("ru.dialog.self"), "concept.agent.self")

    def test_lex_for_locale(self) -> None:
        self.assertEqual(lex_for_locale("concept.orange", "ru"), "lemma.ru.apelsin")
        self.assertEqual(lex_for_locale("concept.orange", "en"), "lemma.en.orange")

    def test_spawn_concept_layer_bootstraps_catalog(self) -> None:
        state = self._state()
        rep = spawn_concept_layer(state)
        self.assertGreaterEqual(len(rep["concept_ids"]), 4)
        zone = ensure_memory_zone(state)
        dom = zone["immutable"]["domains"]["concept"]
        self.assertIn("concept.orange", dom["concept_ids"])
        self.assertIn(CONCEPT_CORE_LATTICE, agent_lattices(state))

    def test_normalize_bind_blocks_dedupes_by_hub(self) -> None:
        blocks = normalize_bind_blocks(
            [
                block_dict("lemma.ru.apelsin", "апельсин", source="kb", score=12),
                block_dict("lemma.en.orange", "orange", source="kb", score=10),
                block_dict("lang.word.apelsin", "апельсин", source="kb", score=8),
            ]
        )
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["concept_id"], "concept.orange")
        self.assertIn("surface_concept_id", blocks[0])

    def test_binder_dedupe_uses_concept_hub(self) -> None:
        rows = _dedupe_blocks(
            [
                {"concept_id": "lemma.ru.okno", "text": "окно", "source": "kb", "score": 9},
                {"concept_id": "lemma.en.window", "text": "window", "source": "kb", "score": 8},
            ]
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["concept_id"], "concept.window")

    def test_discourse_budget_collapses_lex_to_one_hub_score(self) -> None:
        budget = discourse_budget_from_blocks(
            [
                {"concept_id": "lemma.ru.apelsin", "score": 20},
                {"concept_id": "lemma.en.orange", "score": 18},
            ],
            query_intent="discuss",
        )
        self.assertGreaterEqual(budget.score_floor, 4)

    def test_spawn_concept_prism_earned_entry(self) -> None:
        state = self._state()
        rep = spawn_concept_prism(state, "concept.orange", provenance="earned", theory_id="earned-test")
        self.assertEqual(rep["concept_id"], "concept.orange")

    def test_concept_honesty_gate_passes(self) -> None:
        state = self._state()
        spawn_concept_layer(state)
        report = build_concept_honesty_report(state)
        self.assertTrue(report["gate_pass"])
        with tempfile.TemporaryDirectory() as tmp:
            path = write_concept_honesty_artifact(Path(tmp), report)
            self.assertTrue(path.is_file())


if __name__ == "__main__":
    unittest.main()
