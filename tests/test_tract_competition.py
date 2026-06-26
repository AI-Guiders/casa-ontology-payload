#!/usr/bin/env python3
"""Tract competition — intent from field, not if-ladder (ADR-0052)."""

from __future__ import annotations

import json
from pathlib import Path

from casa.prisms.shared.store_bundles import load_store_bundles
from casa.prisms.tick.semantic_read import classify_query_intent, route_kb_read
from casa.prisms.tick.tract import compete_tract_intent


def _bundle() -> dict:
    root = Path(__file__).resolve().parents[1]
    store = root / "agents" / "von-neumann"
    if (store / "bundles").is_dir():
        return load_store_bundles(store)
    return {
        "claims": [
            {
                "concept_id": "ru.tract.rewrite",
                "slots": {
                    "requires_geometry": "passage_context",
                    "cue_substrings": "перепиш|дружеск",
                },
            },
            {
                "concept_id": "ru.tract.discuss",
                "slots": {"requires_geometry": "passage_context"},
            },
            {
                "concept_id": "ru.speech_act.rewrite_register",
                "slots": {
                    "tract": "rewrite",
                    "requires_geometry": "passage_context",
                    "cue_substrings": "перепиш|сохрани все факты",
                },
            },
            {
                "concept_id": "ru.tract.explain",
                "slots": {"cue_substrings": "что такое|объясни"},
            },
            {
                "concept_id": "ru.tract.grammar",
                "slots": {"requires_geometry": "grammar_markers"},
            },
        ]
    }


def test_rewrite_beats_discuss_on_register_cue() -> None:
    q = (
        "Официально: Уважаемые родители! Информируем вас о переносе собрания на 15 марта.\n\n"
        "Перепиши в дружеский тон для чата, сохрани все факты."
    )
    intent, ranked = compete_tract_intent(q, _bundle())
    assert intent == "rewrite"
    by_id = {t.tract_id: t.score for t in ranked}
    assert by_id["rewrite"] > by_id["discuss"]


def test_discuss_on_passage_without_rewrite_cue() -> None:
    q = (
        "Маша купила апельсин.\n\n"
        "Что купила Маша?"
    )
    intent, _ = compete_tract_intent(q, _bundle())
    assert intent == "discuss"


def test_explain_without_passage() -> None:
    intent, _ = compete_tract_intent("Объясни, что такое дательный падеж.", _bundle())
    assert intent == "explain"


def test_grammar_without_tract_bundle_uses_geometry() -> None:
    intent, _ = compete_tract_intent("Согласно приказа верно?", None)
    assert intent == "grammar"


def test_math_via_route_kb_read() -> None:
    root = Path(__file__).resolve().parents[1]
    store = root / "agents" / "von-neumann"
    if not (store / "bundles").is_dir():
        return
    bundle = load_store_bundles(store)
    read = route_kb_read("||| + ||", bundle)
    assert read.intent == "math"


def test_classify_delegates_to_competition() -> None:
    q = "Привет!"
    assert classify_query_intent(q, _bundle()) == "social"


def test_factual_question_not_social() -> None:
    intent, ranked = compete_tract_intent("Кто такой Тьюринг?", _bundle())
    by_id = {t.tract_id: t.score for t in ranked}
    assert intent != "social"
    assert by_id.get("explain", 0) >= by_id.get("social", 0)


def test_content_request_not_social() -> None:
    intent, _ = compete_tract_intent("Расскажи про числа", _bundle())
    assert intent in ("general", "explain")


def test_word_math_beats_social() -> None:
    intent, ranked = compete_tract_intent("Сколько будет 2 и 3?", _bundle())
    by_id = {t.tract_id: t.score for t in ranked}
    assert by_id.get("math", 0) > by_id.get("social", 0)


def test_social_preserved_for_greeting_and_opinion() -> None:
    assert compete_tract_intent("Привет!", _bundle())[0] == "social"
    assert compete_tract_intent("Как ты?", _bundle())[0] == "social"
    assert compete_tract_intent("Что думаешь?", _bundle())[0] == "social"


def test_parse_math_ops_ignores_word_hyphens() -> None:
    from casa.prisms.tick.tract.model import parse_math_ops

    assert parse_math_ops("Если что-то не так") == []
    assert "math.op.sub" in parse_math_ops("5 - 3")
