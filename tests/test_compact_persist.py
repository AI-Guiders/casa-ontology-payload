#!/usr/bin/env python3
"""Compact persist: multi-prism export/import round-trip."""

from __future__ import annotations

import json
from pathlib import Path

from casa.prisms.memory.memory_prisms import content_prism_lattices, ensure_prisms
from casa.prisms.memory.prism_spawn import spawn_content_lattice, spawn_prism
from casa.prisms.shared.compact_persist import compact_persist_store
from casa.prisms.shared.export_ltm_pack import export_pack, iter_profile_lattice_exports
from casa.prisms.shared.import_ltm_pack import import_pack


def test_iter_profile_lattice_exports_all_content_prisms():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 1})
    spawn_prism(state, "prism_math", kind="content")
    spawn_content_lattice(state, "prism_math", "schema-math", z_level=0)
    spawn_prism(state, "prism_lang_ru", kind="content")
    spawn_content_lattice(state, "prism_lang_ru", "lexicon-test", z_level=2)

    exports = iter_profile_lattice_exports(state)
    prisms_seen = {pid for pid, _, _ in exports}
    assert "prism_math" in prisms_seen
    assert "prism_lang_ru" in prisms_seen
    assert any(lid == "schema-math" for _, lid, _ in exports)
    assert any(lid == "lexicon-test" for _, lid, _ in exports)


def test_compact_persist_round_trip_multi_prism(tmp_path: Path) -> None:
    store = tmp_path / "store-test"
    store.mkdir()
    ltm = store / "ltm"
    ltm.mkdir()
    (ltm / "pack.manifest.json").write_text(
        json.dumps({"schema_version": 1, "format": "ltm-pack", "lattices": {}}),
        encoding="utf-8",
    )

    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 3})
    spawn_prism(state, "prism_math", kind="content")
    lat = spawn_content_lattice(state, "prism_math", "schema-math", z_level=0)
    lats = content_prism_lattices(state, "prism_math")
    lats["schema-math"]["cells"][0] = ["W:test", "C:math.demo"]

    report = compact_persist_store(store, state, reason="test")
    assert report["manifest_totals"]["lattice_count"] >= 1
    assert (ltm / "meta" / "router.json").is_file()

    manifest = json.loads((ltm / "pack.manifest.json").read_text(encoding="utf-8"))
    assert "prism_math" in (manifest.get("prisms") or {})
    assert manifest["lattices"]["schema-math"]["prism_id"] == "prism_math"

    fresh = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    imp = import_pack(fresh, ltm, manifest=manifest)
    assert "prism_math" in (imp.get("loaded_by_prism") or {})
    reloaded = content_prism_lattices(fresh, "prism_math")
    assert "schema-math" in reloaded
    assert reloaded["schema-math"]["cells"][0]


def test_export_pack_backward_compat_single_layer(tmp_path: Path) -> None:
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    spawn_content_lattice(state, "prism_memory", "L3_phrase", z_level=3)
    out = tmp_path / "ltm"
    manifest = export_pack(state, out, lattice_ids=["L3_phrase"], include_control=False)
    assert manifest["lattices"]["L3_phrase"]["prism_id"] == "prism_memory"
