#!/usr/bin/env python3
"""agent-concept-core index + NCA edge policy (ADR-0073 P19)."""

from __future__ import annotations

import unittest

from casa.domain.dialogue_bind.blocks import block_dict
from casa.prisms.memory.agent_prism import agent_lattices, ensure_agent_prism
from casa.prisms.memory.concept_index import (
    CONCEPT_CORE_LATTICE,
    apply_concept_nca_edge_decay,
    build_concept_hub_index,
    concept_index_snapshot,
    hub_token,
    nca_protected_tokens,
    touch_concept_hub_edges,
)
from casa.prisms.memory.concept_layer import spawn_concept_layer
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.nca_codec import tokens_from_lattice
from casa.prisms.memory.zone import spawn_memory_zone


class ConceptIndexTests(unittest.TestCase):
    def _state(self) -> dict:
        state = ensure_prisms({"field_version": 0})
        ensure_agent_prism(state)
        spawn_memory_zone(state)
        spawn_concept_layer(state)
        return state

    def test_build_index_places_hub_and_edges(self) -> None:
        state = self._state()
        snap = concept_index_snapshot(state)
        self.assertGreaterEqual(snap["hub_count"], 4)
        self.assertGreater(snap["edge_count"], 0)
        lat = agent_lattices(state)[CONCEPT_CORE_LATTICE]
        toks = tokens_from_lattice(lat)
        self.assertIn(hub_token("concept.orange"), toks)

    def test_touch_edges_on_bind(self) -> None:
        state = self._state()
        blocks = [
            block_dict("lemma.ru.apelsin", "апельсин", source="kb", score=12),
        ]
        from casa.prisms.memory.concept_layer import normalize_bind_blocks

        rep = touch_concept_hub_edges(state, normalize_bind_blocks(blocks), tick=1)
        self.assertGreaterEqual(rep["touched_hubs"], 1)
        self.assertGreaterEqual(rep["touched_edges"], 1)

    def test_nca_decay_protects_hub_tokens(self) -> None:
        state = self._state()
        protected = nca_protected_tokens(state)
        self.assertIn(hub_token("concept.window"), protected)
        before = tokens_from_lattice(agent_lattices(state)[CONCEPT_CORE_LATTICE])
        self.assertIn(hub_token("concept.window"), before)
        rep = apply_concept_nca_edge_decay(state)
        after = tokens_from_lattice(agent_lattices(state)[CONCEPT_CORE_LATTICE])
        self.assertIn(hub_token("concept.window"), after)
        self.assertGreaterEqual(rep["hub_tokens_kept"], 1)


if __name__ == "__main__":
    unittest.main()
