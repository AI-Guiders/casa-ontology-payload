#!/usr/bin/env python3
"""ADR-0021 — transfer matrix bootstrap and route fallback."""

from __future__ import annotations

from casa.domain.routing import RouteContext, Router
from casa.domain.transfer_matrix import load_transfer_matrix, routes_from_transfer_matrix
from casa.prisms.memory.memory_prisms import content_prism_lattices, ensure_prisms
from casa.prisms.memory.prism_spawn import ensure_multi_prism_bootstrap, spawn_content_lattice
from casa.prisms.memory.prism_router import resolve_route
from casa.prisms.shared.prism_state import PRISM_LANG_RU, PRISM_MEMORY


def test_transfer_matrix_loads_routes():
    data = load_transfer_matrix()
    assert data.get("schema_version") == "casa_transfer_matrix_v1"
    routes = routes_from_transfer_matrix(locale="ru")
    assert any(r.match.get("modality") == "t9" for r in routes)
    assert any(r.target_prism == PRISM_LANG_RU for r in routes)


def test_bootstrap_registers_domain_stubs_and_routes():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    from casa.prisms.shared.prism_state import prisms

    assert PRISM_LANG_RU in prisms(state)
    routes = Router.bind(state).routes()
    assert len(routes) >= 4


def test_resolve_fallback_to_memory_when_domain_empty():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    ensure_multi_prism_bootstrap(state)
    spawn_content_lattice(state, PRISM_MEMORY, "L2_word", z_level=2)
    content_prism_lattices(state, PRISM_MEMORY)["L2_word"]["cells"][0] = ["W:test"]
    target = resolve_route(state, RouteContext(modality="t9", locale="ru"))
    assert target.prism_id == PRISM_MEMORY
    assert (target.matched or {}).get("logical_prism") == PRISM_LANG_RU
