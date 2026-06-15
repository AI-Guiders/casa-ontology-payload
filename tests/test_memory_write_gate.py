#!/usr/bin/env python3
"""Immutable memory write gate (ADR-0068 P12g / ADR-0069 P13d-e)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from casa._paths import REPO_ROOT
from casa.prisms.memory.agent_canon_lattice import agent_promote_canon_lattice
from casa.prisms.memory.memory_prisms import (
    append_episode,
    ensure_prisms,
    import_lattice_into_prism,
    memory_lattices,
    run_sleep,
)
from casa.prisms.memory.write_gate import (
    ImmutableLatticeWriteError,
    assert_memory_write_allowed,
    is_immutable_lattice,
    memory_write_allowed,
    record_earned_postulate,
    sync_immutable_catalog,
)
from casa.prisms.memory.zone import ensure_memory_zone, spawn_memory_zone

BUNDLE = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"


class MemoryWriteGateTests(unittest.TestCase):
    def test_schema_math_is_immutable(self) -> None:
        state = ensure_prisms({"field_version": 0})
        spawn_memory_zone(state)
        self.assertTrue(is_immutable_lattice(state, "schema-math"))
        self.assertFalse(memory_write_allowed(state, "schema-math", context="hot"))
        self.assertFalse(memory_write_allowed(state, "schema-math", context="sleep_merge"))
        self.assertTrue(memory_write_allowed(state, "schema-math", context="promote_canon"))

    def test_hot_import_blocked_for_immutable(self) -> None:
        state = ensure_prisms({"field_version": 0})
        spawn_memory_zone(state)
        lats = memory_lattices(state)
        lat = dict(lats.get("schema-math") or {"width": 8, "height": 8, "cells": [[] for _ in range(64)]})
        with self.assertRaises(ImmutableLatticeWriteError):
            import_lattice_into_prism(state, "prism_memory", "schema-math", lat)

    def test_sleep_skips_immutable_episodes(self) -> None:
        if not BUNDLE.is_file():
            self.skipTest("math bundle missing")
        bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
        state = ensure_prisms({"field_version": 0})
        spawn_memory_zone(state)
        append_episode(
            state,
            cue="3",
            surface_attempt="?",
            correct="3",
            lattice_id="schema-math",
            concept_id="math.num.three",
            scene="lab",
        )
        rep = run_sleep(state, bundle, strength=2)
        skipped = rep.get("immutable_skipped") or []
        self.assertTrue(skipped)
        self.assertEqual(skipped[0].get("lattice_id"), "schema-math")
        self.assertEqual(skipped[0].get("reason"), "immutable_sleep_gate")

    def test_sync_immutable_catalog_indexes_bootstrap(self) -> None:
        state = ensure_prisms({"field_version": 0})
        spawn_memory_zone(state)
        meta = state.setdefault("meta", {})
        meta["zone_lattice_index"] = {
            "schema-math": {
                "mutability": "immutable",
                "domain": "math",
                "owner_zone": "memory",
            },
            "lexicon-ru": {
                "mutability": "mutable",
                "domain": "lang",
                "owner_zone": "memory",
            },
        }
        rep = sync_immutable_catalog(state)
        zone = ensure_memory_zone(state)
        self.assertIn("schema-math", zone["immutable"]["lattice_ids"])
        self.assertNotIn("lexicon-ru", zone["immutable"]["lattice_ids"])
        self.assertGreaterEqual(rep["immutable_lattice_count"], 1)

    def test_record_earned_postulate_sets_active_theory(self) -> None:
        state = ensure_prisms({"field_version": 3})
        spawn_memory_zone(state)
        earned = record_earned_postulate(
            state,
            lattice_id="math-axiom",
            domain="math",
            theory_id="math-axiom",
            concept_ids=["math.axiom.peano1"],
        )
        self.assertEqual(earned["theory_id"], "math-axiom")
        self.assertEqual(state["meta"]["active_theory_id"], "math-axiom")
        theories = ensure_memory_zone(state)["immutable"]["theories"]
        active = [t for t in theories if t.get("active")]
        self.assertEqual(len(active), 1)
        self.assertIn("math-axiom", active[0]["lattice_ids"])

    def test_promote_canon_records_earned_theory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            (store / "bundles").mkdir(parents=True)
            state = ensure_prisms({"field_version": 1})
            spawn_memory_zone(state)
            rep = agent_promote_canon_lattice(
                store,
                state,
                {
                    "lattice_id": "math-axiom",
                    "concept_ids": ["math.axiom.peano1"],
                    "reason": "held-out check passed",
                    "allow_unconfirmed": True,
                },
                persist=False,
                allow_unconfirmed=True,
                operator_sign=True,
            )
            self.assertTrue(rep.get("promoted"))
            self.assertEqual(rep.get("earned_theory", {}).get("theory_id"), "math-axiom")
            self.assertTrue(memory_write_allowed(state, "math-axiom", context="promote_canon"))
            assert_memory_write_allowed(state, "math-axiom", context="promote_canon")


if __name__ == "__main__":
    unittest.main()
