#!/usr/bin/env python3
"""WM co-place — no cross-family garbage edges in partner bind."""

from __future__ import annotations

from casa.domain.dialogue_bind.partner_scope import apply_partner_bind_scope
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.wm.bind import (
    _co_place_pair_allowed,
    wm_bind_focus_concepts,
    wm_blocks_for_bind,
)
from casa.prisms.memory.wm import place_wm_edge, spawn_wm_lattice
from casa.prisms.memory.wm.lattice import wm_root


def test_co_place_rejects_lang_word_with_math_entity() -> None:
    assert not _co_place_pair_allowed("lang.word.квантовый", "math.entity.stick")
    assert not _co_place_pair_allowed("math.op.div", "ru.dialog.how_are_you")
    assert _co_place_pair_allowed("lang.word.привет", "ru.dialog.how_are_you")
    assert _co_place_pair_allowed("math.op.div", "math.entity.stick")


def test_social_wm_bind_skips_cross_family_placement() -> None:
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 1})
    wm_bind_focus_concepts(
        state,
        ["lang.word.квантовый", "math.entity.stick", "ru.dialog.affect"],
        tick=1,
        intent="social",
    )
    root = wm_root(state)
    edge_text = " ".join(
        f"{e.get('from_concept')} {e.get('to_concept')}"
        for meta in root.values()
        for e in (meta.get("edges") or {}).values()
    )
    assert "math.entity.stick" not in edge_text
    assert "math.op.div" not in edge_text


def test_social_wm_blocks_need_query_overlap() -> None:
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 1})
    spawn_wm_lattice(state, tick=1)
    place_wm_edge(state, "lang.word.квантовый", "lang.word.физика", tick=1)
    assert wm_blocks_for_bind(state, "Как ты?", intent="social") == []
    blocks = wm_blocks_for_bind(
        state, "Как мы говорили про квантовый — напомни.", intent="social", k=2
    )
    assert blocks


def test_partner_scope_strips_wm_from_social_bind() -> None:
    rows = [
        {"concept_id": "ru.dialog.affect", "source": "kb", "score": 80},
        {
            "concept_id": "agent.wm.edge.test",
            "source": "wm_prism",
            "score": 50,
            "text": "WM-связь",
        },
    ]
    scoped = apply_partner_bind_scope(rows, intent="social")
    assert all(r.get("source") != "wm_prism" for r in scoped)
    assert any(r.get("concept_id") == "ru.dialog.affect" for r in scoped)
