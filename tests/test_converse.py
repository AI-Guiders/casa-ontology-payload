"""Deep routing: answer a clean domain clause via the conceptual network, else fall through.

answer_clause confirms a valid situation (normalised meaning + memory), explains a category
error, and returns None for anything that is not a clean domain clause (casual chat).
"""

from __future__ import annotations

import functools

from casa.curriculum.converse import answer_clause, looks_domain
from casa.curriculum.world import build_meaning_state


@functools.lru_cache(maxsize=1)
def _state() -> tuple[dict, str]:
    return build_meaning_state()


def test_looks_domain_prefilter() -> None:
    assert looks_domain("яблоко на столе") is True
    assert looks_domain("собака ест мясо") is True
    assert looks_domain("привет") is False
    assert looks_domain("у меня совсем нет свободного времени сегодня вечером") is False  # too long


def test_valid_clause_is_confirmed_and_remembered() -> None:
    state, lat = _state()
    r = answer_clause(state, lat, "яблоко лежит на столе")
    assert r is not None and "Яблоко на столе" in r
    # a paraphrase is recognised as the same / similar situation just stored
    again = answer_clause(state, lat, "на столе яблоко")
    assert again is not None and ("Понял" in again)


def test_category_error_is_explained() -> None:
    state, lat = _state()
    assert "не получается" in (answer_clause(state, lat, "идея на столе") or "")
    assert "не получается" in (answer_clause(state, lat, "собака ест камень") or "")


def test_casual_lines_fall_through() -> None:
    state, lat = _state()
    assert answer_clause(state, lat, "у меня нет времени") is None
    assert answer_clause(state, lat, "привет как дела") is None
    assert answer_clause(state, lat, "расскажи про погоду") is None
