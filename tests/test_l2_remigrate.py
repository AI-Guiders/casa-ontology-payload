#!/usr/bin/env python3
"""L2 monolith remigrate before ltm export."""

from __future__ import annotations

from pathlib import Path

from casa.prisms.memory.l2_remigrate import LTM_VOCAB_U16_MAX, remigrate_l2_from_monolith
from casa.prisms.memory.lexicon_shard import LEGACY_L2, ensure_l2_lattice, lattice_vocab_size, sharding_config
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.memory.vocab import _strengthen_word_on_l2
from casa.prisms.shared.export_ltm_pack import export_pack


def test_remigrate_splits_to_shards_and_exports(tmp_path: Path) -> None:
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    words = [f"w{i:05d}" for i in range(200)]
    cfg = sharding_config(state)
    cfg["enabled"] = False
    state["l2_sharding"] = cfg
    ensure_l2_lattice(state, LEGACY_L2)
    for w in words:
        _strengthen_word_on_l2(state, w, copies=1)

    assert lattice_vocab_size(memory_lattices(state)[LEGACY_L2]) > 100
    rep = remigrate_l2_from_monolith(state, words=words, copies=1, num_shards=8)
    assert rep["status"] == "ok"
    assert rep["max_shard_vocab"] <= LTM_VOCAB_U16_MAX

    manifest = export_pack(state, tmp_path / "ltm", remigrate_l2=False)
    assert manifest["totals"]["lattice_count"] >= 8
    shard_ids = [k for k in manifest["lattices"] if k.startswith("L2_word_")]
    assert len(shard_ids) >= 8
    if LEGACY_L2 in manifest["lattices"]:
        assert int(manifest["lattices"][LEGACY_L2]["file_bytes"]) < 200
