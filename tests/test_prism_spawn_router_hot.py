#!/usr/bin/env python3
"""ADR-0016: spawn prisms, router, hot-context."""

from __future__ import annotations

from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.memory.prism_hot_context import (
    add_hot_edge,
    apply_hot_boost_to_ranked,
    hot_digest_for_cue,
    hot_neighbors,
    hot_word_salience_for_cue,
    prune_hot_context,
)
from casa.prisms.memory.prism_router import (
    RouteContext,
    add_route,
    bootstrap_default_routes,
    resolve_route,
    router_routes,
)
from casa.prisms.memory.prism_spawn import (
    ensure_default_router_and_hot,
    list_content_prism_ids,
    spawn_content_lattice,
    spawn_prism,
)
from casa.prisms.shared.prism_state import (
    PRISM_HOT_CONTEXT,
    PRISM_MEMORY,
    PRISM_ROUTER,
    active_prism_id,
    prism_kind,
)


def test_spawn_content_prism_and_lattice():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    spawn_prism(state, "prism_lang_ru", kind="content", make_active=True)
    spawn_content_lattice(state, "prism_lang_ru", "lexicon-test", z_level=2, concept_prefix="lang.word.")
    assert active_prism_id(state) == "prism_lang_ru"
    lats = memory_lattices(state, "prism_lang_ru")
    assert "lexicon-test" in lats
    assert "prism_lang_ru" in list_content_prism_ids(state)


def test_hot_context_edges_only():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 1})
    ensure_default_router_and_hot(state)
    assert prism_kind(state, PRISM_HOT_CONTEXT) == "hot_context"
    add_hot_edge(state, "cue:дом", "denotes", "lang.word.дом", salience=2.0)
    nbr = hot_neighbors(state, "cue:дом")
    assert nbr and nbr[0]["dst"] == "lang.word.дом"
    digest = hot_digest_for_cue(state, "дом")
    assert "lang.word.дом" in digest
  # no lattice in hot prism
    from casa.prisms.shared.prism_state import prism_hot_context

    assert not prism_hot_context(state).get("lattices")


def test_router_resolves_schema_and_t9():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    ensure_default_router_and_hot(state)
    spawn_prism(state, "prism_math", kind="content")
    spawn_content_lattice(state, "prism_math", "schema-math")
    add_route(state, {"modality": "schema"}, "prism_math", lattice_hint="schema-math", priority=200)
    add_route(state, {"modality": "t9", "locale": "ru"}, PRISM_MEMORY, priority=10)

    math = resolve_route(state, RouteContext(modality="schema"))
    assert math.prism_id == "prism_math"
    assert math.lattice_hint == "schema-math"

    t9 = resolve_route(state, RouteContext(modality="t9", locale="ru"))
    assert t9.prism_id == PRISM_MEMORY

    default = resolve_route(state, RouteContext())
    assert default.prism_id == PRISM_MEMORY


def test_bootstrap_routes_on_ensure_default():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    ensure_default_router_and_hot(state)
    routes = router_routes(state)
    assert len(routes) >= 2
    assert any((r.get("match") or {}).get("modality") == "t9" for r in routes)
    again = bootstrap_default_routes(state)
    assert len(again) == len(routes)


def test_profile_default_content_prism():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    ensure_default_router_and_hot(state)
    spawn_prism(state, "prism_math", kind="content")
    state["store"] = {"default_content_prism": "prism_math"}
    target = resolve_route(state, RouteContext(modality="unknown_mod"))
    assert target.prism_id == "prism_math"
    assert (target.matched or {}).get("source") == "profile"


def test_hot_boost_reorders_candidates():
    ranked = [("домой", 10), ("дом", 8), ("домашний", 6)]
    boosted = apply_hot_boost_to_ranked(ranked, {"дом": 3.0})
    assert boosted[0][0] == "дом"


def test_hot_word_salience_from_edges():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 1})
    ensure_default_router_and_hot(state)
    add_hot_edge(state, "cue:дом", "denotes", "lang.word.дом", salience=2.5)
    boosts = hot_word_salience_for_cue(state, "дом")
    assert boosts.get("дом") == 2.5


def test_prune_hot_context_ttl():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 100})
    ensure_default_router_and_hot(state)
    add_hot_edge(state, "a", "link", "b", salience=0.01, ttl_ticks=1)
    state["field_version"] = 200
    rep = prune_hot_context(state, min_salience=0.05)
    assert rep["removed"] >= 1
