#!/usr/bin/env python3
"""Tract competition geometry signals."""

from __future__ import annotations

import re

from casa.prisms.tick.passage.comprehend import has_passage_context, passage_focus_question
from casa.prisms.tick.tract.model import parse_math_ops, parse_stick_runs


def _passage_focus(query: str) -> str:
    return passage_focus_question(query)


def geometry_signals(query: str) -> dict[str, bool]:
    """Structural turn shape — no tract-specific Russian lists here."""
    from casa.prisms.control.sn_cen_runtime import _query_has_grammar_intent, _query_is_dialogue

    raw = (query or "").strip()
    focus = _passage_focus(raw)
    words = re.findall(r"[\w\u0400-\u04FF]+", focus, flags=re.UNICODE)
    ql = focus.lower()
    math_words = any(
        w in ql
        for w in ("плюс", "минус", "умнож", "делить", "палоч", "слагаем", "сумм", "разност", "сколько")
    )
    has_digits = bool(re.search(r"\d", ql))
    word_math = math_words or (
        has_digits and any(w in ql for w in ("сколько", "будет", "равн", "слож", "вычит", "умнож"))
    )
    wh_heads = (
        "кто",
        "какой",
        "какая",
        "какие",
        "какое",
        "где",
        "когда",
        "сколько",
        "чей",
        "чья",
        "чьё",
        "чьи",
        "кому",
        "кого",
        "чему",
        "чем",
    )
    factual_question = "?" in focus and any(
        re.search(rf"\b{re.escape(head)}\b", ql, flags=re.UNICODE) for head in wh_heads
    ) and not re.search(r"\bкак\b", ql, flags=re.UNICODE)
    if "?" in focus and re.search(r"\bчто\b", ql, flags=re.UNICODE):
        factual_question = factual_question or any(
            p in ql for p in ("что такое", "что за", "что значит", "что означает")
        )
        if any(w in ql for w in ("думаешь", "думаете", "считаешь", "чувствуешь")):
            factual_question = False
    content_request = any(
        w in ql for w in ("расскажи", "рассказать", "опиши", "описать", "перечисли", "перечислить")
    )
    return {
        "passage_context": has_passage_context(raw),
        "math_glyph": bool(parse_stick_runs(raw) or parse_math_ops(raw) or math_words),
        "word_math": word_math,
        "brief_turn": len(words) <= 6,
        "short_turn": len(words) <= 10,
        "question_mark": "?" in focus,
        "long_turn": len(words) > 28,
        "grammar_markers": _query_has_grammar_intent(ql),
        "word_lookup": any(m in ql for m in ("что означает", "что такое", "объясни", "объяснить")),
        "factual_question": factual_question,
        "content_request": content_request,
        "why_passage": any(m in ql for m in ("почему", "зачем")),
        "dialogue_turn": _query_is_dialogue(raw),
        "recall_cue": any(
            m in ql
            for m in ("напомни", "напомин", "ты помнишь", "ты говорил", "мы говорили")
        ),
    }


def _geometry_score_for_tract(tract_id: str, geo: dict[str, bool]) -> tuple[int, list[str]]:
    score = 0
    sources: list[str] = []
    if tract_id == "math" and geo.get("math_glyph"):
        score += 40
        sources.append("geo:math_glyph")
    if tract_id == "math" and geo.get("word_math") and not geo.get("math_glyph"):
        score += 34
        sources.append("geo:word_math")
    if tract_id == "grammar" and geo.get("grammar_markers"):
        score += 34
        sources.append("geo:grammar_markers")
    if tract_id == "recall" and geo.get("recall_cue"):
        score += 34
        sources.append("geo:recall_cue")
    if tract_id == "explain" and geo.get("word_lookup"):
        if geo.get("passage_context") and geo.get("why_passage"):
            score += 8
            sources.append("geo:explain_in_passage_why")
        else:
            score += 36
            sources.append("geo:word_lookup")
    if tract_id == "explain" and geo.get("factual_question") and not geo.get("word_lookup"):
        score += 30
        sources.append("geo:factual_question")
    if tract_id == "general" and geo.get("content_request"):
        score += 22
        sources.append("geo:content_request")
    if tract_id == "social" and geo.get("dialogue_turn") and not geo.get("word_lookup"):
        if not geo.get("math_glyph") and not geo.get("grammar_markers"):
            if not geo.get("factual_question") and not geo.get("content_request") and not geo.get("word_math"):
                score += 32
                sources.append("geo:dialogue_turn")
    if tract_id == "discuss" and geo.get("passage_context"):
        score += 22
        sources.append("geo:passage")
        if geo.get("why_passage"):
            score += 24
            sources.append("geo:why_passage")
    if tract_id == "rewrite" and geo.get("passage_context"):
        score += 14
        sources.append("geo:passage_rewrite_candidate")
    if tract_id == "general" and geo.get("long_turn"):
        score += 8
        sources.append("geo:long_turn")
    return score, sources
