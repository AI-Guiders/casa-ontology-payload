#!/usr/bin/env python3
"""Passage bind geometry + emergent discuss compose (no template if-ladder)."""

from __future__ import annotations

from casa.prisms.tick.passage import passage_sentence_bind_rows


def test_sentence_bind_ranks_by_overlap() -> None:
    passage = "Маша пошла в магазин. Она купила апельсин."
    q = "Что купила Маша?"
    rows = passage_sentence_bind_rows(passage, q)
    assert rows
    assert rows[0][2] >= rows[-1][2]
    assert any("апельсин" in row[1].lower() for row in rows)


def test_discuss_compose_from_passage_blocks() -> None:
    from casa.prisms.tick.articulation_realize import UtterancePlan
    from casa.prisms.tick.phrase_compose import compose_subject_phrase

    q = "Маша пошла в магазин. Она купила апельсин.\n\nЧто купила Маша?"
    blocks = [
        {
            "concept_id": "passage.sent.1",
            "text": "Она купила апельсин.",
            "score": 42,
            "source": "passage",
            "section": "passage_sent",
        },
        {
            "concept_id": "passage.surface.апельсин",
            "text": "«апельсин»",
            "score": 22,
            "source": "passage",
            "section": "passage_lattice",
        },
        {
            "concept_id": "lang.word.апельсин",
            "text": "«апельсин» — фрукт.",
            "score": 30,
            "source": "kb",
            "section": "passage",
            "slots": {"word": "апельсин"},
        },
    ]
    reply = compose_subject_phrase(
        UtterancePlan(act="", intent="ответ по запросу"),
        q,
        blocks=blocks,
        query_intent="discuss",
        stance="confident",
    )
    assert reply
    assert "апельсин" in reply.lower()


def test_discuss_bind_passage_words_only(tmp_path) -> None:
    from casa.domain.dialogue_bind import gather_subject_dialogue_blocks
    from casa.prisms.control.fpn_state import WorkingMemory
    from casa.prisms.memory.memory_prisms import ensure_prisms

    store = tmp_path / "agent"
    store.mkdir()
    bundle = {
        "claims": [
            {"concept_id": "lang.word.апельсин", "text": "«апельсин» — фрукт.", "slots": {"word": "апельсин"}},
            {"concept_id": "lang.word.хлеб", "text": "«хлеб» — еда.", "slots": {"word": "хлеб"}},
            {"concept_id": "ru.dialog.farewell", "text": "прощание", "slots": {"surface": "пока"}},
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
        store,
        bundle=bundle,
    )
    top = [str(b.get("concept_id")) for b in ctx.blocks[:12]]
    assert any("апельсин" in c for c in top)
    assert any(c.startswith("passage.sent.") for c in top)
    assert "lang.word.хлеб" not in top
    assert not any(c.startswith("ru.dialog.") for c in top)
