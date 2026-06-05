#!/usr/bin/env python3
"""ADR-0020: domain round-trip and router parity."""

from __future__ import annotations

from casa.domain.field_state import FieldState
from casa.domain.lattice import Lattice
from casa.domain.persistence import field_state_from_dict, field_state_to_dict
from casa.domain.routing import RouteContext, Router
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.prism_router import add_route, resolve_route


def test_field_state_round_trip_lattice():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    field = field_state_from_dict(state)
    mem = field.catalog.require("prism_memory")
    mem.block.setdefault("lattices", {})["test_lat"] = Lattice(
        lattice_id="test_lat",
        width=4,
        height=4,
        cells=[[] for _ in range(16)],
        concept_prefix="lang.word.",
    ).to_dict()
    wire = field_state_to_dict(field)
    assert wire["prisms"]["prism_memory"]["lattices"]["test_lat"]["width"] == 4


def test_router_domain_matches_legacy_resolve():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    Router.bind(state).bootstrap_defaults(locale="ru")
    add_route(state, {"modality": "schema"}, "prism_memory", lattice_hint="schema-math", priority=200)
    ctx = RouteContext(modality="t9", locale="ru")
    legacy = resolve_route(state, ctx)
    domain = Router.bind(state).resolve(ctx)
    assert domain.prism_id == legacy.prism_id


def test_router_vis_route():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    Router.bind(state).bootstrap_defaults()
    target = Router.bind(state).resolve(RouteContext(modality="vis"))
    assert target.prism_id == "prism_visual"
    assert target.lattice_hint in ("V1_object", "V1_lum")
