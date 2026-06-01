"""L3 phrase monolith remigrate before ltm export."""

from __future__ import annotations

from pathlib import Path

from casa.prisms.memory.l2_remigrate import LTM_VOCAB_U16_MAX
from casa.prisms.memory.l3_remigrate import needs_l3_remigrate, remigrate_l3_from_monolith
from casa.prisms.memory.lexicon_shard import lattice_vocab_size
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.memory.phrase_shard import LEGACY_L3, L3_SHARD_PREFIX, copy_token_to_lattice, empty_l3_lattice
from casa.prisms.shared.export_ltm_pack import export_pack


def _monolith_with_tokens(n: int) -> dict:
    lat = empty_l3_lattice()
    for i in range(n):
        tok = f"C:entity.test.{i:05d}"
        copy_token_to_lattice(lat, tok, [(i % 32, (i // 32) % 32)])
    return lat


def test_remigrate_l3_splits_and_exports(tmp_path: Path) -> None:
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    state.setdefault("sss", {})["lattices"] = {LEGACY_L3: _monolith_with_tokens(180)}
    lats = memory_lattices(state)

    assert lattice_vocab_size(lats[LEGACY_L3]) == 180
    assert needs_l3_remigrate(state)

    rep = remigrate_l3_from_monolith(state, num_shards=8, clear_monolith=True)
    assert rep["status"] == "ok"
    assert rep["max_shard_vocab"] <= LTM_VOCAB_U16_MAX

    state2 = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    state2.setdefault("sss", {})["lattices"] = {LEGACY_L3: _monolith_with_tokens(180)}
    rep_par = remigrate_l3_from_monolith(
        state2, num_shards=8, clear_monolith=True, parallel_workers=4
    )
    assert rep_par["status"] == "ok"
    assert rep_par.get("parallel_workers", 1) >= 2

    manifest = export_pack(state, tmp_path / "ltm", remigrate_l2=False, remigrate_l3=False)
    shard_ids = [k for k in manifest["lattices"] if k.startswith(L3_SHARD_PREFIX)]
    assert len(shard_ids) >= 8
    assert lattice_vocab_size(lats.get(LEGACY_L3) or {}) < 10
