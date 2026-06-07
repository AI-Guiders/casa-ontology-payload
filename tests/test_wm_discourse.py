#!/usr/bin/env python3
"""WM link discourse — compose from wm_prism blocks (ADR-0055)."""

from __future__ import annotations

from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.wm import place_wm_edge, spawn_wm_lattice
from casa.prisms.tick.phrase_compose import _wm_link_discourse, compose_subject_phrase
from casa.prisms.tick.articulation_realize import UtterancePlan


def _wm_block(fc: str, tc: str, *, score: int = 24) -> dict:
    return {
        "concept_id": "agent.wm.edge.test",
        "text": f"WM: {fc} ↔ {tc}",
        "source": "wm_prism",
        "score": score,
        "slots": {"from": fc, "to": tc, "sigma": 0.55},
    }


def test_wm_link_discourse_rain_cancel() -> None:
    blocks = [_wm_block("ru.prop.rain", "ru.prop.cancel")]
    q = "Объясни связь между дождём и отменой."
    body = _wm_link_discourse(q, blocks)
    assert body
    assert "дожд" in body.lower()
    assert "отмен" in body.lower()


def test_compose_subject_phrase_explain_from_wm() -> None:
    blocks = [_wm_block("ru.prop.rain", "ru.prop.cancel")]
    q = "Объясни связь между дождём и отменой."
    body = compose_subject_phrase(
        UtterancePlan(act="explain", intent="explain", atoms=[]),
        q,
        blocks=blocks,
        query_intent="explain",
        stance="partial",
    )
    assert body
    assert "дожд" in body.lower()


def test_wm_callback_retention_phrase() -> None:
    blocks = [_wm_block("lang.word.квантовый", "lang.word.физика")]
    q = "Как мы говорили про квантовый — напомни связь."
    body = compose_subject_phrase(
        UtterancePlan(act="social", intent="social", atoms=[]),
        q,
        blocks=blocks,
        query_intent="social",
        stance="partial",
    )
    assert body
    assert "квантов" in body.lower()


def test_wm_with_lattice_state() -> None:
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 1})
    spawn_wm_lattice(state, tick=1)
    place_wm_edge(state, "ru.prop.rain", "ru.prop.cancel", tick=1)
    from casa.prisms.memory.wm import wm_blocks_for_bind

    blocks = wm_blocks_for_bind(state, "связь между дождём и отменой", k=2)
    body = _wm_link_discourse("связь между дождём и отменой", blocks)
    assert body and "дожд" in body.lower()
