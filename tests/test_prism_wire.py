#!/usr/bin/env python3
"""ADR-0020 M4: prism_wire kind inference and domain parity."""

from __future__ import annotations

from casa.domain.prism import prism_from_block
from casa.domain.prism_ids import (
    PRISM_HIPPO,
    PRISM_HOT_CONTEXT,
    PRISM_KIND_CONTENT,
    PRISM_KIND_HOT_CONTEXT,
    PRISM_KIND_ROUTER,
    PRISM_MEMORY,
    PRISM_ROUTER,
)
from casa.domain.prism_wire import (
    infer_prism_kind,
    normalize_prisms,
    prism_kind,
    prism_memory,
    prism_supports_lattices,
    wire_used_legacy_format,
)


def test_infer_prism_kind_explicit_and_heuristic():
    assert infer_prism_kind(PRISM_HOT_CONTEXT, {}) == PRISM_KIND_HOT_CONTEXT
    assert infer_prism_kind(PRISM_ROUTER, {"kind": "router"}) == PRISM_KIND_ROUTER
    assert infer_prism_kind("prism_lang_ru", {}) == PRISM_KIND_CONTENT
    assert infer_prism_kind(PRISM_HIPPO, {}) == "hippo"


def test_prism_from_block_matches_wire_helpers():
    state = normalize_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    prism_memory(state)
    block = state["prisms"][PRISM_MEMORY]
    p = prism_from_block(PRISM_MEMORY, block)
    assert p.kind == PRISM_KIND_CONTENT
    assert p.supports_lattices is True
    assert prism_kind(state, PRISM_MEMORY) == PRISM_KIND_CONTENT
    assert prism_supports_lattices(state, PRISM_MEMORY) is True


def test_wire_used_legacy_format_detects_cylinder_keys():
    state = {
        "schema_version": "multi_cylinder_v1",
        "cylinders": {},
    }
    assert wire_used_legacy_format(state) is True
    normalize_prisms(state)
    assert wire_used_legacy_format(state) is False


def test_normalize_legacy_cylinders():
    state = {
        "schema_version": "multi_cylinder_v1",
        "cylinders": {"cyl_memory": {"subsystem": "sss", "lattices": {}}},
        "sn": {"active_cylinder": "cyl_memory"},
    }
    normalize_prisms(state)
    assert "prisms" in state
    assert "prism_memory" in state["prisms"]
    assert state["sn"]["active_prism"] == "prism_memory"
