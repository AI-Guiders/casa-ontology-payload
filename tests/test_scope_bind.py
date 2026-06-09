#!/usr/bin/env python3
"""Scoped bind hot path (ADR-0068 P12b)."""

from __future__ import annotations

import unittest

from casa.prisms.intelligence.scope_bind import (
    apply_bind_scope,
    bind_scope,
    filter_bind_blocks,
    lattice_allowed_for_bind,
    scoped_lattice_ids,
)
from casa.prisms.memory.write_gate import record_earned_postulate
from casa.prisms.memory.zone import spawn_memory_zone
from casa.prisms.intelligence.zone_prism_map import load_zone_prism_map, memory_resolve_scopes


class ScopeBindTests(unittest.TestCase):
    def _state_with_index(self) -> dict:
        return {
            "meta": {
                "zone_lattice_index": {
                    "schema-math": {
                        "owner_zone": "memory",
                        "domain": "math",
                        "memory_subkind": "semantic",
                    },
                    "phrases-01": {
                        "owner_zone": "memory",
                        "domain": "lang",
                        "memory_subkind": "semantic",
                    },
                    "agent-wm-scratch": {
                        "owner_zone": "memory",
                        "domain": "lang",
                        "memory_subkind": "semantic",
                    },
                    "agent-logical-core": {
                        "owner_zone": "logical",
                        "intelligence_zone": "logical",
                    },
                }
            }
        }

    def test_math_scope_excludes_phrases(self) -> None:
        state = self._state_with_index()
        rep = apply_bind_scope(state, tract="math", client_zone="logical")
        allowed = set(rep["scope"]["semantic_domains"])
        self.assertEqual(allowed, {"math"})
        doc = load_zone_prism_map()
        scope = memory_resolve_scopes(doc, tract="math", client_zone="logical")
        lats = scoped_lattice_ids(state, scope)
        assert lats is not None
        self.assertIn("schema-math", lats)
        self.assertNotIn("phrases-01", lats)

    def test_filter_bind_blocks_drops_out_of_scope_wm(self) -> None:
        state = self._state_with_index()
        apply_bind_scope(state, tract="math", client_zone="logical")
        blocks = [
            {
                "concept_id": "wm.edge.1",
                "text": "math wm",
                "source": "wm_prism",
                "score": 10,
                "slots": {"lattice_id": "schema-math"},
            },
            {
                "concept_id": "wm.edge.2",
                "text": "lang wm",
                "source": "wm_prism",
                "score": 10,
                "slots": {"lattice_id": "phrases-01"},
            },
            {
                "concept_id": "math.op.add",
                "text": "add",
                "source": "kb",
                "score": 20,
            },
        ]
        filtered = filter_bind_blocks(blocks, state, intent="math")
        lids = [
            str(b.get("slots", {}).get("lattice_id") or "")
            for b in filtered
            if isinstance(b.get("slots"), dict)
        ]
        self.assertIn("schema-math", lids)
        self.assertNotIn("phrases-01", lids)
        self.assertEqual(len(filtered), 2)

    def test_agent_scratch_always_allowed(self) -> None:
        state = self._state_with_index()
        doc = load_zone_prism_map()
        scope = memory_resolve_scopes(doc, tract="math", client_zone="logical", state=state)
        self.assertTrue(lattice_allowed_for_bind(state, "agent-logical-core", scope))

    def test_math_scope_includes_active_theory_lattices(self) -> None:
        state = self._state_with_index()
        from casa.prisms.memory.memory_prisms import ensure_prisms

        ensure_prisms(state)
        spawn_memory_zone(state)
        record_earned_postulate(
            state,
            lattice_id="math-axiom",
            domain="math",
            theory_id="math-axiom",
            concept_ids=["math.axiom.peano1"],
        )
        scope = bind_scope(state, tract="math", client_zone="logical")
        self.assertEqual(scope.get("active_theory_id"), "math-axiom")
        lats = scoped_lattice_ids(state, scope)
        assert lats is not None
        self.assertIn("math-axiom", lats)


if __name__ == "__main__":
    unittest.main()
