"""LTM u16 vocab cap health (warn / over / remigrate hints)."""

from __future__ import annotations

from casa.prisms.memory.l2_remigrate import LTM_VOCAB_U16_MAX
from casa.prisms.memory.ltm_vocab_health import (
    LTM_VOCAB_WARN_AT,
    OP_ENSURE_L2_SHARDS,
    OP_L3_PHRASE_SHARD,
    ltm_vocab_shard_health,
    maintain_ltm_vocab_health,
)
from casa.prisms.memory.lexicon_shard import LEGACY_L2, ensure_l2_lattice, sharding_config
from casa.prisms.memory.vocab import _strengthen_word_on_l2
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.prism_memory_health import run_prism_memory_health


def test_ltm_vocab_soft_warn(monkeypatch):
    def fake_size(lat: dict) -> int:
        return int(lat.get("_vocab", 0))

    monkeypatch.setattr("casa.prisms.memory.ltm_vocab_health.lattice_vocab_size", fake_size)
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    state.setdefault("sss", {})["lattices"] = {
        "L2_word_00": {"width": 32, "height": 32, "cells": [], "_vocab": LTM_VOCAB_WARN_AT},
    }
    rep = ltm_vocab_shard_health(state)
    assert rep["ok"] is True
    assert len(rep["near_cap"]) == 1
    assert rep["near_cap"][0]["lattice_id"] == "L2_word_00"


def test_ltm_vocab_over_cap_fails(monkeypatch):
    def fake_size(lat: dict) -> int:
        return int(lat.get("_vocab", 0))

    monkeypatch.setattr("casa.prisms.memory.ltm_vocab_health.lattice_vocab_size", fake_size)
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    state.setdefault("sss", {})["lattices"] = {
        "L3_phrase": {"width": 32, "height": 32, "cells": [], "_vocab": LTM_VOCAB_U16_MAX + 1},
    }
    rep = ltm_vocab_shard_health(state)
    assert rep["ok"] is False
    assert rep["over_cap"][0]["lattice_id"] == "L3_phrase"
    assert OP_L3_PHRASE_SHARD in rep["pending_kernel_ops"]


def test_maintain_ltm_vocab_repairs_l2_monolith():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    words = [f"w{i:04d}" for i in range(120)]
    cfg = sharding_config(state)
    cfg["enabled"] = False
    state["l2_sharding"] = cfg
    ensure_l2_lattice(state, LEGACY_L2)
    for w in words:
        _strengthen_word_on_l2(state, w, copies=1)

    rep = maintain_ltm_vocab_health(state, auto_repair_l2=True, auto_compact=False)
    assert rep["status"] == "repaired_l2"
    assert any(r.get("op") == OP_ENSURE_L2_SHARDS for r in rep["repaired"])
    assert rep["after"]["needs_l2_remigrate"] is False


def test_prism_memory_health_includes_ltm_vocab(monkeypatch):
    def fake_size(lat: dict) -> int:
        return int(lat.get("_vocab", 0))

    monkeypatch.setattr("casa.prisms.memory.ltm_vocab_health.lattice_vocab_size", fake_size)
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    from casa.prisms.memory.prism_spawn import ensure_default_router_and_hot

    ensure_default_router_and_hot(state)
    state.setdefault("sss", {})["lattices"] = {
        "L2_word_00": {"width": 32, "height": 32, "cells": [], "_vocab": LTM_VOCAB_WARN_AT},
    }
    rep = run_prism_memory_health(state)
    assert any(c["id"] == "ltm_vocab_soft" for c in rep["checks"])
    assert rep.get("ltm_layout") or any(c.get("aspect") == "ltm_layout" for c in rep["checks"])
