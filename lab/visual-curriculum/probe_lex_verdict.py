"""Probe verdict: top score tie = «не знаю» (ambiguous), not a miss."""

from __future__ import annotations

from typing import Any

from casa.prisms.memory.meta_concept_aliases import canonical_lex_concept_id


def leaders_at_max_score(preds: list[tuple[str, int]]) -> tuple[int, list[str]]:
    if not preds:
        return 0, []
    max_s = max(s for _, s in preds)
    return max_s, [c for c, s in preds if s == max_s]


def verdict_lex_probe(
    preds: list[tuple[str, int]],
    hint: str,
) -> dict[str, Any]:
    """Classify teacher probe outcome.

    - know: единственный лидер по score и он совпал с hint
    - ambiguous: несколько concept на max score (ничья = «не знаю»)
    - wrong: единственный лидер, но не hint
    - empty: нет hint или нет сигнала с поля
    """
    hint = canonical_lex_concept_id(str(hint or "").strip())
    if not hint:
        return {
            "verdict": "empty",
            "teacher_guess": None,
            "matches_hint": False,
            "top_score": 0,
            "leaders": [],
        }
    top_score, leaders = leaders_at_max_score(preds)
    if not leaders:
        return {
            "verdict": "empty",
            "teacher_guess": None,
            "matches_hint": False,
            "top_score": 0,
            "leaders": [],
        }
    teacher_guess = preds[0][0]
    if len(leaders) > 1:
        return {
            "verdict": "ambiguous",
            "teacher_guess": teacher_guess,
            "matches_hint": False,
            "top_score": top_score,
            "leaders": leaders,
        }
    if leaders[0] == hint:
        return {
            "verdict": "know",
            "teacher_guess": leaders[0],
            "matches_hint": True,
            "top_score": top_score,
            "leaders": leaders,
        }
    return {
        "verdict": "wrong",
        "teacher_guess": leaders[0],
        "matches_hint": False,
        "top_score": top_score,
        "leaders": leaders,
    }
