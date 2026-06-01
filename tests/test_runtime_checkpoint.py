#!/usr/bin/env python3
"""Thin runtime checkpoint: ltm bodies + small JSON overlay."""

from __future__ import annotations

import json
from pathlib import Path

from casa.prisms.memory.memory_prisms import content_prism_lattices, ensure_prisms
from casa.prisms.memory.prism_hot_context import add_hot_edge, hot_neighbors
from casa.prisms.memory.prism_spawn import spawn_content_lattice, spawn_prism
from casa.prisms.shared.compact_persist import compact_persist_store
from casa.prisms.shared.runtime_checkpoint import (
    THIN_CHECKPOINT_FORMAT,
    build_thin_snapshot,
    is_thin_checkpoint_file,
    merge_thin_overlay,
)
from casa.prisms.shared.store_layout import STORE_TIER_RUNTIME
from casa.prisms.shared.store_persist import load_runtime_state, save_runtime_state


def test_build_thin_snapshot_strips_cells():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 1})
    spawn_content_lattice(state, "prism_memory", "L3_phrase", z_level=3)
    lats = content_prism_lattices(state)
    lats["L3_phrase"]["cells"][0] = ["W:hello"]

    thin = build_thin_snapshot(state)
    assert thin["checkpoint_format"] == THIN_CHECKPOINT_FORMAT
    stripped = thin["prisms"]["prism_memory"]["lattices"]["L3_phrase"]
    assert stripped.get("_cells_in_ltm") is True
    assert stripped["cells"] == []


def test_thin_checkpoint_round_trip(tmp_path: Path) -> None:
    store = tmp_path / "store-thin"
    store.mkdir()
    ltm = store / "ltm"
    ltm.mkdir()
    (ltm / "pack.manifest.json").write_text(
        json.dumps({"schema_version": 1, "format": "ltm-pack", "lattices": {}}),
        encoding="utf-8",
    )

    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 2})
    spawn_prism(state, "prism_math", kind="content")
    spawn_content_lattice(state, "prism_math", "schema-math", z_level=0)
    content_prism_lattices(state, "prism_math")["schema-math"]["cells"][0] = ["W:pi", "C:math.pi"]
    add_hot_edge(state, "cue:pi", "denotes", "math.pi", salience=3.0)

    compact_persist_store(store, state, reason="test")
    save_runtime_state(store, state, force=True)

    fs = store / "field_state.json"
    assert is_thin_checkpoint_file(fs)
    assert fs.stat().st_size < 500_000

    loaded = load_runtime_state(store)
    assert loaded["boot_source"] == STORE_TIER_RUNTIME
    booted = loaded["state"]
    assert booted.get("store", {}).get("boot_source") == "ltm+thin_checkpoint"
    math = content_prism_lattices(booted, "prism_math")
    assert math["schema-math"]["cells"][0]
    assert hot_neighbors(booted, "cue:pi")


def test_build_thin_snapshot_strips_hippo_lattice_cells():
    from casa.prisms.memory.memory_prisms import empty_hippo_lattice
    from casa.prisms.shared.lattice_names_v1 import EPISODIC_SURFACE
    from casa.prisms.shared.prism_state import prism_hippo

    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 1})
    hip = prism_hippo(state)
    hip["lattices"][EPISODIC_SURFACE] = empty_hippo_lattice()
    hip["lattices"]["H0_episode"] = empty_hippo_lattice(width=32, height=32)
    hip["lattices"]["H0_episode"]["cells"][0] = ["ep:stub"]

    thin = build_thin_snapshot(state)
    for lid in ("H0_episode", EPISODIC_SURFACE):
        lat = thin["prisms"]["prism_hippo"]["lattices"][lid]
        assert lat.get("_cells_in_ltm") is True
        assert lat["cells"] == []
    assert thin["prisms"]["prism_hippo"]["episodes"] == []


def test_build_thin_snapshot_omits_last_sleep_items():
    state = ensure_prisms(
        {
            "schema_version": "multi_prism_v1",
            "field_version": 1,
            "consolidation": {
                "last_sleep": {"merged": 2, "items": [{"id": "a"}, {"id": "b"}]},
            },
        }
    )
    thin = build_thin_snapshot(state)
    last = thin["consolidation"]["last_sleep"]
    assert "items" not in last
    assert last["items_omitted"] == 2
    assert last["merged"] == 2


def test_merge_thin_overlay_keeps_episodes():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    spawn_content_lattice(state, "prism_memory", "L3_phrase", z_level=3)
    content_prism_lattices(state)["L3_phrase"]["cells"][0] = ["W:from_ltm"]

    thin = build_thin_snapshot(state)
    thin["prisms"].setdefault("prism_hippo", {})["episodes"] = [{"id": "ep-1", "cue": "test"}]

    merged = merge_thin_overlay(ensure_prisms({"schema_version": "multi_prism_v1"}), thin)
    assert merged["prisms"]["prism_hippo"]["episodes"][0]["id"] == "ep-1"
