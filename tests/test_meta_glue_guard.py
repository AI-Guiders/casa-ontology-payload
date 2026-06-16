#!/usr/bin/env python3
"""Meta-glue guard — referent active suppresses situation-only promise hubs."""

from __future__ import annotations

import json

from casa.domain.dialogue_bind import SubjectDialogueContext
from casa.domain.subject_articulation import compose_subject_utterance
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.tick.discourse.meta_glue_guard import (
    is_meta_glue_dialog_block,
    is_situation_script_block,
    referent_field_active,
    should_suppress_meta_glue_efferent,
)


def _ctx(query: str, blocks: list[dict]) -> SubjectDialogueContext:
    return SubjectDialogueContext(
        display_name="Нейманн",
        field_version=1,
        wm=WorkingMemory(),
        blocks=sorted(blocks, key=lambda b: int(b.get("score") or 0), reverse=True),
        source_tags=["kb", "dialogue"],
        stance="partial",
        query_intent="general",
        runtime_state={},
    )


def test_ask_thought_hub_is_meta_glue() -> None:
    block = {
        "concept_id": "ru.dialog.ask_thought",
        "slots": {
            "situation": "partner_asks_opinion",
            "predicate_lemma": "мнение",
            "object_lemma": "по полю",
            "limit_kind": "без выдумки",
        },
    }
    assert is_meta_glue_dialog_block(block)
    assert should_suppress_meta_glue_efferent(
        block,
        [{"concept_id": "dialog.context.referent", "slots": {"referent_prop": "ru.prop.x"}}],
    )


def test_self_hub_with_predicate_is_situation_script() -> None:
    block = {
        "concept_id": "ru.dialog.self",
        "slots": {
            "situation": "mirror_ack",
            "hedge": "согласен",
            "predicate": "не знаю",
            "scope": "не обязан совпадать",
        },
    }
    assert is_situation_script_block(block)


def test_referent_skips_ask_thought_glue_uses_field() -> None:
    mirror = "Хорошо, я тоже не знаю, но он не обязан совпадать"
    q = "А что ты думаешь про это?"
    blocks = [
        {
            "concept_id": "ru.speech_act.partner.ask_thought",
            "source": "speech_act",
            "score": 46,
            "slots": {"speech_act": "ask_thought", "compose_single_hub": "true"},
        },
        {
            "concept_id": "ru.dialog.ask_thought",
            "source": "kb",
            "score": 90,
            "slots": {
                "situation": "partner_asks_opinion",
                "predicate_lemma": "мнение",
                "object_lemma": "по полю",
                "limit_kind": "без выдумки",
            },
        },
        {
            "concept_id": "ru.dialog.self",
            "source": "kb",
            "score": 55,
            "slots": {
                "situation": "partner_asks_opinion",
                "hedge": "про опыт",
                "predicate": "не знаю",
                "scope": "совпадать не обязан",
            },
        },
        {
            "concept_id": "dialog.context.referent",
            "source": "dialogue",
            "score": 40,
            "slots": {
                "referent_prop": "ru.prop.partner.experience",
                "referent_snippet": mirror,
            },
        },
        {
            "concept_id": "dialog.context.focus_recent",
            "source": "dialogue",
            "score": 38,
            "slots": {
                "thread_terms": "ru.prop.partner.experience",
                "referent_prop": "ru.prop.partner.experience",
            },
        },
        {
            "concept_id": "subject.dialog.partner_recent",
            "source": "dialogue",
            "score": 44,
            "text": f"Партнёр недавно: «{mirror}».",
        },
    ]
    reply = compose_subject_utterance(q, _ctx(q, blocks))
    low = reply.lower()
    assert referent_field_active(blocks)
    assert "без выдумки" not in low
    assert "не знаю" in low or "совпада" in low or "опыт" in low


def test_teaching_thread_suppresses_how_are_you_glue() -> None:
    teaching = (
        "Слушай: когда я спрашиваю «как ты», я хочу услышать про твоё состояние здесь и сейчас."
    )
    query = "Как ты?"
    blocks = [
        {
            "concept_id": "ru.speech_act.partner.how_are_you",
            "source": "speech_act",
            "score": 46,
            "slots": {"speech_act": "how_are_you", "compose_single_hub": "true"},
        },
        {
            "concept_id": "ru.dialog.how_are_you",
            "source": "kb",
            "score": 88,
            "slots": {
                "situation": "partner_asks_state",
                "modifier": "сейчас",
                "surface": "на связи",
                "object_lemma": "с полем",
            },
        },
        {
            "concept_id": "subject.limbic.state",
            "source": "limbic",
            "score": 28,
            "slots": {"valence": "0.05", "arousal": "0.4", "security": "0.52"},
        },
        {
            "concept_id": "dialog.context.focus_recent",
            "source": "dialogue",
            "score": 40,
            "slots": {"thread_terms": "состояние|диалог"},
        },
        {
            "concept_id": "subject.dialog.partner_recent",
            "source": "dialogue",
            "score": 44,
            "text": f"Партнёр недавно: «{teaching}».",
        },
    ]
    reply = compose_subject_utterance(query, _ctx(query, blocks))
    low = reply.lower()
    assert "на связи по полю" not in low
    assert "(пока не могу собрать ответ)" in low


def test_no_referent_meta_glue_still_allowed() -> None:
    q = "Что думаешь?"
    blocks = [
        {
            "concept_id": "ru.dialog.ask_thought",
            "source": "kb",
            "score": 90,
            "slots": {
                "situation": "partner_asks_opinion",
                "predicate_lemma": "мнение",
                "object_lemma": "по полю",
                "limit_kind": "без выдумки",
            },
        },
    ]
    ctx = _ctx(q, blocks)
    reply = compose_subject_utterance(q, ctx)
    plan = (ctx.runtime_state or {}).get("meta", {}).get("neumann_material_plan", {})
    plan_text = json.dumps(plan, ensure_ascii=False).lower()
    assert "без выдумки" not in reply.lower()
    assert "predefined_dialog_label_not_surface" in plan_text
