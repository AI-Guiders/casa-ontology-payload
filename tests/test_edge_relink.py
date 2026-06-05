#!/usr/bin/env python3
"""Kolb relink: weaken old edge, mint new; supersede emergent routes."""

from __future__ import annotations

from casa.domain.edge_relink import agent_relink_crosslink, relink_vis_lex_bridge, supersede_emergent_route
from casa.domain.routing import ROUTE_KIND_CAPABILITY, Router
from casa.prisms.memory.f0_stack import count_edge_copies, graph_edge_token, strengthen_graph_edge, weaken_graph_edge
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices, persist_content_lattices
from casa.prisms.memory.prism_hot_context import add_hot_edge, hot_edges, remove_hot_edge
from casa.prisms.shared.lattice_names_v1 import LEXICON_RU


def test_weaken_graph_edge_removes_copies():
    lats = {LEXICON_RU: {"width": 8, "height": 8, "cells": [[] for _ in range(64)]}}
    strengthen_graph_edge(lats, LEXICON_RU, "vis.lum.frame.x", "co_occurs", "lang.word.a", copies=4)
    tok = graph_edge_token("vis.lum.frame.x", "co_occurs", "lang.word.a")
    assert count_edge_copies(lats[LEXICON_RU], "vis.lum.frame.x", "co_occurs", "lang.word.a") == 4
    removed = weaken_graph_edge(lats, LEXICON_RU, "vis.lum.frame.x", "co_occurs", "lang.word.a")
    assert removed == 4
    assert count_edge_copies(lats[LEXICON_RU], "vis.lum.frame.x", "co_occurs", "lang.word.a") == 0


def test_remove_hot_edge():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    add_hot_edge(state, "vis.lum.frame.a", "co_occurs", "lang.word.b")
    assert remove_hot_edge(state, "vis.lum.frame.a", "co_occurs", "lang.word.b")
    assert not any(
        e.get("dst") == "lang.word.b"
        for e in hot_edges(state)
    )


def test_agent_relink_crosslink_swaps_dst():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    from casa.prisms.memory.lexical_lattice_bootstrap import ensure_lexical_lattices

    ensure_lexical_lattices(state)
    lats = memory_lattices(state)
    strengthen_graph_edge(
        lats, LEXICON_RU, "vis.lum.frame.w1", "co_occurs", "lang.word.wrong", copies=4
    )
    persist_content_lattices(state, lats)
    assert (
        count_edge_copies(lats[LEXICON_RU], "vis.lum.frame.w1", "co_occurs", "lang.word.wrong") == 4
    )

    result = agent_relink_crosslink(
        state,
        old_src="vis.lum.frame.w1",
        old_relation="co_occurs",
        old_dst="lang.word.wrong",
        new_src="vis.lum.frame.w1",
        new_relation="denotes",
        new_dst="lang.word.right",
        gate="self_verify:test",
    )
    lats2 = memory_lattices(state)
    assert result.weakened.get("removed_lattice", 0) >= 4
    assert result.minted is not None
    assert (
        count_edge_copies(lats2.get(LEXICON_RU) or {}, "vis.lum.frame.w1", "co_occurs", "lang.word.wrong")
        == 0
    )
    assert (
        count_edge_copies(lats2.get(LEXICON_RU) or {}, "vis.lum.frame.w1", "denotes", "lang.word.right") >= 4
    )


def test_relink_vis_lex_bridge_wrapper():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    from casa.prisms.memory.lexical_lattice_bootstrap import ensure_lexical_lattices

    ensure_lexical_lattices(state)
    lats = memory_lattices(state)
    strengthen_graph_edge(
        lats, LEXICON_RU, "vis.lum.frame.word-abc-sans", "co_occurs", "lang.word.old", copies=3
    )
    persist_content_lattices(state, lats)

    result = relink_vis_lex_bridge(
        state,
        frame_id="word-abc-sans",
        old_lex_cid="lang.word.old",
        new_lex_cid="lang.word.new",
        gate="kolb:probe",
    )
    assert result.minted is not None
    lats2 = memory_lattices(state)
    assert (
        count_edge_copies(
            lats2.get(LEXICON_RU) or {},
            "vis.lum.frame.word-abc-sans",
            "denotes",
            "lang.word.new",
        )
        >= 3
    )


def test_supersede_emergent_route():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0, "store": {"store_id": "t"}})
    router = Router.bind(state)
    router.add_emergent_route(
        route_kind=ROUTE_KIND_CAPABILITY,
        match={"modality": "vis", "novel": "true"},
        target_skill="skill.read.whole",
        gate="old_gate",
        agent_id="t",
    )
    result = supersede_emergent_route(
        state,
        route_kind=ROUTE_KIND_CAPABILITY,
        match={"modality": "vis", "novel": "true"},
        gate="kolb:analytic",
        agent_id="t",
        target_skill="skill.read.analytic",
    )
    caps = router.routes(route_kind=ROUTE_KIND_CAPABILITY)
    assert len(caps) == 1
    assert caps[0].target_skill == "skill.read.analytic"
    assert result.route_added is not None
