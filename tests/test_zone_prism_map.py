#!/usr/bin/env python3
"""Zone/prism map classification (ADR-0067 P11a)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from casa.prisms.intelligence.zone_prism_map import (
    classify_lattice_id,
    load_zone_prism_map,
    lattices_for_scope,
    memory_resolve_scopes,
    mutability_for_lattice,
    shadow_tract_report,
)


class ZonePrismMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.doc = load_zone_prism_map()

    def test_classify_math_and_lang(self) -> None:
        math = classify_lattice_id("schema-math", self.doc)
        self.assertEqual(math.owner_zone, "memory")
        self.assertEqual(math.domain, "math")
        lang = classify_lattice_id("lexicon-ru-03", self.doc)
        self.assertEqual(lang.domain, "lang")
        phrase = classify_lattice_id("phrases-12", self.doc)
        self.assertEqual(phrase.domain, "lang")

    def test_classify_executive_and_agent(self) -> None:
        ctrl = classify_lattice_id("control-dmn", self.doc)
        self.assertEqual(ctrl.owner_zone, "executive")
        limbic = classify_lattice_id("agent-limbic-core", self.doc)
        self.assertEqual(limbic.owner_zone, "emotional")

    def test_shadow_tract_no_phrase_in_math(self) -> None:
        index = {
            "entries": [
                {"lattice_id": "schema-math", "domain": "math", "memory_subkind": "semantic"},
                {"lattice_id": "phrases-01", "domain": "lang", "memory_subkind": "semantic"},
                {"lattice_id": "lexicon-ru-01", "domain": "lang", "memory_subkind": "semantic"},
            ]
        }
        shadow = shadow_tract_report(index, self.doc)
        self.assertEqual(shadow["math"]["phrase_leak_n"], 0)
        self.assertGreater(shadow["discuss"]["lattice_count"], 0)
        self.assertEqual(shadow["math"]["lattice_count"], 1)

    def test_mutability_canon_vs_lexicon(self) -> None:
        morph = classify_lattice_id("morph-role-ru", self.doc)
        self.assertEqual(mutability_for_lattice("morph-role-ru", morph, self.doc), "immutable")
        lex = classify_lattice_id("lexicon-ru-03", self.doc)
        self.assertEqual(mutability_for_lattice("lexicon-ru-03", lex, self.doc), "mutable")
        scope = memory_resolve_scopes(self.doc, tract="math", client_zone="logical")
        self.assertEqual(scope["semantic_domains"], ["math"])
        lats = lattices_for_scope(
            {"entries": [
                {"lattice_id": "schema-math", "domain": "math", "memory_subkind": "semantic"},
                {"lattice_id": "phrases-01", "domain": "lang", "memory_subkind": "semantic"},
            ]},
            scope,
        )
        self.assertEqual(lats, ["schema-math"])


if __name__ == "__main__":
    unittest.main()
