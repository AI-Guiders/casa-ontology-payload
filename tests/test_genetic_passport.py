#!/usr/bin/env python3
"""Genetic constant wire + genome passport (ADR-0062 P6c / P6f)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from casa.prisms.genetic import (
    build_genome_spec,
    format_genome_passport_repl,
    genetic_constant,
    genome_passport,
    seal_genetic_zone,
    write_genome_passport_artifact,
)
from casa.prisms.memory.agent_prism import ensure_agent_prism
from casa.prisms.memory.forgetting import DEFAULT_PRIMING_ALPHA, priming_alpha_retain
from casa.prisms.memory.intent.policy import get_intent_policy
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.wm.policy import get_wm_policy
from casa.prisms.intelligence.genetic_wire import wire_genetic_intelligence_zone


class GeneticPassportTests(unittest.TestCase):
    def _state(self) -> dict:
        state = ensure_prisms({"field_version": 0})
        ensure_agent_prism(state)
        return state

    def test_genetic_constant_reads_forgetting_genotype(self) -> None:
        state = self._state()
        val = genetic_constant(state, "forgetting_genotype.implicit.priming_alpha_retain")
        self.assertEqual(val, 0.2)
        self.assertEqual(priming_alpha_retain(state), 0.2)

    def test_seal_writes_genome_and_passport(self) -> None:
        state = self._state()
        cfg = build_genome_spec({"species_id": "casa.test.v1"})
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            rep = seal_genetic_zone(store, state, cfg, tick=0)
            self.assertTrue(rep.get("sealed"))
            self.assertTrue((store / "agent" / "genome.v1.json").is_file())
            passport_path = store / "genome_passport.json"
            self.assertTrue(passport_path.is_file())
            doc = genome_passport(state)
            self.assertEqual(doc["species_id"], "casa.test.v1")
            self.assertTrue(doc.get("valid"))
            self.assertIn("allele_summary", doc)
            self.assertEqual(
                doc["allele_summary"]["forgetting_genotype"]["priming_alpha_retain"],
                0.2,
            )

    def test_wm_intent_policy_wired_from_genome(self) -> None:
        state = self._state()
        wm = get_wm_policy(state)
        intent = get_intent_policy(state)
        self.assertEqual(wm["theta_decay"], genetic_constant(state, "signal_decay.wm_theta_decay"))
        self.assertEqual(intent["theta_decay"], genetic_constant(state, "signal_decay.intent_theta_decay"))

    def test_wire_genetic_zone_includes_alleles(self) -> None:
        state = self._state()
        block = wire_genetic_intelligence_zone(state)
        self.assertIn("allele_summary", block)
        self.assertIn("forgetting_genotype", block["allele_summary"])

    def test_format_repl_digest(self) -> None:
        state = self._state()
        text = format_genome_passport_repl(state)
        self.assertIn("species_id", text)
        self.assertIn("forgetting", text)

    def test_priming_alpha_matches_default_genome(self) -> None:
        state = self._state()
        self.assertEqual(priming_alpha_retain(state), DEFAULT_PRIMING_ALPHA)


if __name__ == "__main__":
    unittest.main()
