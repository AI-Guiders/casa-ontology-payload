#!/usr/bin/env python3
"""Discuss path — passage meaning, not templates."""

from __future__ import annotations

from casa.domain.subject_articulation import compose_subject_utterance
from casa.domain.dialogue_bind import SubjectDialogueContext, gather_subject_dialogue_blocks
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.tick.semantic_read import classify_query_intent


def test_passage_intent_is_discuss() -> None:
    q = "Маша купила хлеб.\n\nЧто купила Маша?"
    assert classify_query_intent(q) == "discuss"


def test_discuss_buy_answer() -> None:
    from casa.domain.subject_articulation import compose_subject_utterance
    from casa.prisms.memory.memory_prisms import ensure_prisms

    bundle = {
        "claims": [
            {
                "concept_id": "lang.word.апельсин",
                "text": "«апельсин» — фрукт.",
                "slots": {"word": "апельсин"},
            },
            {
                "concept_id": "ru.meta.discourse.from_text",
                "text": "linkers",
                "slots": {"linker_2": "и"},
            },
        ]
    }
    q = "Маша пошла в магазин. Она купила апельсин.\n\nЧто купила Маша?"
    ctx = gather_subject_dialogue_blocks(
        q,
        None,
        ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0}),
        WorkingMemory(),
        None,
        bundle=bundle,
    )
    reply = compose_subject_utterance(q, ctx)
    assert reply
    assert "апельсин" in reply.lower()
    assert "слышу:" not in reply.lower()


def test_gather_discuss(tmp_path) -> None:
    from casa.prisms.memory.memory_prisms import ensure_prisms

    store = tmp_path / "agent"
    store.mkdir()
    bundle = {
        "claims": [
            {
                "concept_id": "lang.word.апельсин",
                "text": "«апельсин» — фрукт.",
                "slots": {"word": "апельсин"},
            }
        ]
    }
    q = "Маша купила апельсин.\n\nЧто купила Маша?"
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    ctx = gather_subject_dialogue_blocks(q, None, state, WorkingMemory(), store, bundle=bundle)
    assert ctx.query_intent == "discuss"
    reply = compose_subject_utterance(q, ctx)
    assert "апельсин" in reply.lower()
