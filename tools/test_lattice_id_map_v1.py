#!/usr/bin/env python3
"""Canonical lattice id constants (runtime — no legacy resolution)."""

from __future__ import annotations

import unittest

from lattice_names_v1 import (  # type: ignore
    CONTROL_DMN,
    CONTROL_STACK,
    EPISODIC_SURFACE,
    SCHEMA_MATH,
    alphabet_id,
    has_control_lattice,
    missing_control_lattices,
    require_lattice,
    words_shard_id,
)


class TestLatticeIdsV1(unittest.TestCase):
    def test_control_stack_constants(self) -> None:
        self.assertEqual(CONTROL_DMN, "control-dmn")
        self.assertIn("control-predict", CONTROL_STACK)
        self.assertEqual(len(CONTROL_STACK), 7)

    def test_math_and_episodic(self) -> None:
        self.assertEqual(SCHEMA_MATH, "schema-math")
        self.assertEqual(EPISODIC_SURFACE, "episodic-surface")

    def test_require_lattice_strict(self) -> None:
        lats = {"control-dmn": {}}
        self.assertEqual(require_lattice("control-dmn", lats), "control-dmn")
        with self.assertRaises(KeyError):
            require_lattice("lattice_dmn", lats)

    def test_missing_control_no_legacy(self) -> None:
        missing = missing_control_lattices({"control-dmn": {}})
        self.assertNotIn("control-dmn", missing)
        self.assertIn("control-predict", missing)

    def test_has_control_probe(self) -> None:
        self.assertTrue(has_control_lattice({"control-dmn": {}}))
        self.assertFalse(has_control_lattice({"lattice_dmn": {}}))

    def test_words_shard_id(self) -> None:
        self.assertEqual(words_shard_id("ru", 7), "words-ru-07")
        self.assertEqual(alphabet_id("ru"), "alphabet-ru")


if __name__ == "__main__":
    unittest.main()
