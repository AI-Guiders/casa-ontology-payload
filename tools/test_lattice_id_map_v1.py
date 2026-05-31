#!/usr/bin/env python3
"""Lattice id map v1 — legacy → canonical kebab."""

from __future__ import annotations

import unittest

from lattice_names_v1 import legacy_to_v1, resolve_store_lattice_id, v1_to_legacy  # type: ignore


class LatticeIdMapV1Tests(unittest.TestCase):
    def test_math_and_control(self) -> None:
        self.assertEqual(legacy_to_v1("F2_quantity"), "cardinal-math")
        self.assertEqual(legacy_to_v1("lattice_predict"), "control-predict")
        self.assertEqual(v1_to_legacy("control-dmn"), "lattice_dmn")

    def test_episodic_monolith(self) -> None:
        self.assertEqual(legacy_to_v1("H0_episode"), "episodic-surface")
        self.assertEqual(legacy_to_v1("H1_surface"), "episodic-surface")

    def test_resolve_store_prefers_v1(self) -> None:
        lats = {"control-dmn": {}, "lattice_dmn": {}}
        self.assertEqual(resolve_store_lattice_id("lattice_dmn", lats), "control-dmn")
        self.assertEqual(resolve_store_lattice_id("control-dmn", lats), "control-dmn")

    def test_words_shard_pattern(self) -> None:
        self.assertEqual(legacy_to_v1("L2_word_07"), "words-ru-07")
        self.assertEqual(legacy_to_v1("words-ru-07"), "words-ru-07")


if __name__ == "__main__":
    unittest.main()
