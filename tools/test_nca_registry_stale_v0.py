#!/usr/bin/env python3
"""Unit checks for NCA stale detection vs control-only field_version bumps."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from field_version_v0 import bump_control_field_version, bump_memory_field_version  # type: ignore
from nca_registry_v0 import (  # type: ignore
    find_stale_shards,
    lattice_train_fingerprint,
    mark_lattice_trained,
    save_registry,
    empty_registry,
)
from sss_nca_codec_v0 import tokens_from_lattice  # type: ignore


def _memory_lattice(tokens: list[str]) -> dict:
    cells: list[list[str]] = [[] for _ in range(4)]
    for i, t in enumerate(tokens):
        cells[i % 4].append(t)
    return {"width": 2, "height": 2, "cells": cells}


def _state_with_shard(lid: str, tokens: list[str], *, field_version: int = 6) -> dict:
    return {
        "schema_version": "multi_prism_v1",
        "field_version": field_version,
        "prisms": {
            "prism_memory": {
                "lattices": {lid: _memory_lattice(tokens)},
            }
        },
        "sharding": {"mode": "lexicographic", "num_shards": 64},
    }


class NcaStaleControlBumpTests(unittest.TestCase):
    def test_control_bump_does_not_stale_unchanged_l2_legacy_registry(self) -> None:
        lid = "words-ru-00"
        toks = [f"C:lang.word.w{i}" for i in range(10)]
        state = _state_with_shard(lid, toks, field_version=6)
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            (store / "nca" / lid).mkdir(parents=True)
            (store / "nca" / lid / "model.pt").write_bytes(b"fake")
            reg = empty_registry(store_id=store.name)
            reg["lattices"][lid] = {
                "last_trained_at": "2026-01-01T00:00:00+00:00",
                "field_version_at_train": 6,
                "token_count_at_train": len(toks),
                "model_path": f"nca/{lid}/model.pt",
            }
            save_registry(store, reg)
            bump_control_field_version(state)
            self.assertEqual(state["control"]["field_version"], 1)
            self.assertEqual(state["field_version"], 6)
            stale = find_stale_shards(state, store, min_tokens=8)
            self.assertEqual(stale, [])

    def test_content_change_stale_with_fingerprint(self) -> None:
        lid = "words-ru-00"
        toks = [f"C:lang.word.w{i}" for i in range(10)]
        state = _state_with_shard(lid, toks, field_version=6)
        lat = state["prisms"]["prism_memory"]["lattices"][lid]
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            (store / "nca" / lid).mkdir(parents=True)
            (store / "nca" / lid / "model.pt").write_bytes(b"fake")
            mark_lattice_trained(store, state, lid, lattice=lat)
            lat["cells"][0].append("C:lang.word.new")
            stale = find_stale_shards(state, store, min_tokens=8)
            self.assertEqual(len(stale), 1)
            self.assertIn("content_drift", stale[0]["reasons"])

    def test_memory_bump_stale_when_fingerprint_recorded(self) -> None:
        lid = "words-ru-00"
        toks = [f"C:lang.word.w{i}" for i in range(10)]
        state = _state_with_shard(lid, toks, field_version=6)
        lat = state["prisms"]["prism_memory"]["lattices"][lid]
        fp = lattice_train_fingerprint(lat)
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            (store / "nca" / lid).mkdir(parents=True)
            (store / "nca" / lid / "model.pt").write_bytes(b"fake")
            mark_lattice_trained(store, state, lid, lattice=lat)
            bump_memory_field_version(state)
            lat2 = state["prisms"]["prism_memory"]["lattices"][lid]
            lat2["cells"][0].append("C:lang.word.extra")
            self.assertNotEqual(lattice_train_fingerprint(lat2), fp)
            stale = find_stale_shards(state, store, min_tokens=8)
            self.assertEqual(len(stale), 1)
            self.assertIn("content_drift", stale[0]["reasons"])


if __name__ == "__main__":
    unittest.main()
