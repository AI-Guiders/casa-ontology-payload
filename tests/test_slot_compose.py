#!/usr/bin/env python3
"""Slot composer unit tests — L1/L3 assembly from lexical material (ADR-0081)."""

from __future__ import annotations

from casa.domain.subject_articulation import compose_subject_utterance
from casa.domain.dialogue_bind import SubjectDialogueContext
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.tick.discourse.material import (
    build_afferent_event,
    build_material_plan,
    build_text_understanding,
    candidates_from_blocks,
    render_material_plan,
)
from casa.prisms.tick.discourse.slot_compose import compose_lexical_slots


def test_l3_compose_how_are_you_slots() -> None:
    slots = {
        "situation": "partner_asks_state",
        "modifier": "сейчас",
        "surface": "на связи",
        "object_lemma": "с полем",
    }
    text = compose_lexical_slots(slots, tokens={"как", "ты"}, has_question_mark=True)
    low = (text or "").lower()
    assert "сейчас" in low
    assert "связ" in low
    assert "поле" in low


def test_minimal_formula_thanks() -> None:
    slots = {"stimulus": "спасибо", "response": "пожалуйста"}
    assert compose_lexical_slots(slots, tokens={"спасибо"}) == "пожалуйста."


def test_ask_thought_overlay_from_field() -> None:
    slots = {
        "situation": "partner_asks_opinion",
        "predicate_lemma": "мнение",
        "object_lemma": "по полю",
        "limit_kind": "без выдумки",
    }
    text = compose_lexical_slots(
        slots,
        tokens={"что", "думаешь", "про", "это"},
        has_question_mark=True,
        object_overlay="магазин",
        relation_marker="про",
    )
    low = (text or "").lower()
    assert "мнен" in low
    assert "магазин" in low
    assert "по полю" not in low


def test_subject_compose_how_are_you_from_slots() -> None:
    blocks = [
        {
            "concept_id": "ru.dialog.how_are_you",
            "source": "kb",
            "score": 90,
            "slots": {
                "situation": "partner_asks_state",
                "modifier": "сейчас",
                "surface": "на связи",
                "object_lemma": "с полем",
            },
        },
    ]
    ctx = SubjectDialogueContext(
        display_name="Нейманн",
        field_version=1,
        wm=WorkingMemory(),
        blocks=blocks,
        query_intent="general",
        runtime_state={},
    )
    reply = compose_subject_utterance("Как ты?", ctx).lower()
    assert "связ" in reply or "поле" in reply
    assert "(пока не могу собрать ответ)" not in reply


def test_material_plan_selects_lexical_hub_for_question() -> None:
    event = build_afferent_event("Как ты?")
    trace = build_text_understanding(event)
    blocks = [
        {
            "concept_id": "ru.dialog.how_are_you",
            "source": "kb",
            "score": 90,
            "slots": {
                "modifier": "сейчас",
                "surface": "на связи",
                "object_lemma": "с полем",
            },
        },
    ]
    candidates = candidates_from_blocks(trace, blocks)
    plan = build_material_plan(trace, candidates)
    assert plan.renderer_mode == "slot_compose"
    assert plan.selected and plan.selected[0].candidate_id == "ru.dialog.how_are_you"
    surface = render_material_plan(plan)
    assert surface and "связ" in surface.lower()
