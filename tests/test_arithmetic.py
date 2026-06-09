"""Deterministic two-operand arithmetic realizer (honest chat evaluator)."""

from __future__ import annotations

from casa.domain.arithmetic import arithmetic_reply, compute, number_to_ru, parse_arithmetic


def test_glyph_forms() -> None:
    assert parse_arithmetic("2+3") == (2, "+", 3)
    assert parse_arithmetic("10 / 2") == (10, "/", 2)
    assert parse_arithmetic("3*3=?") == (3, "*", 3)
    assert parse_arithmetic("5 - 2") == (5, "-", 2)
    assert parse_arithmetic("4 × 2") == (4, "*", 2)


def test_word_forms() -> None:
    assert parse_arithmetic("два плюс три") == (2, "+", 3)
    assert parse_arithmetic("Сколько будет три умножить на три?") == (3, "*", 3)
    assert parse_arithmetic("десять разделить на два") == (10, "/", 2)
    assert parse_arithmetic("пять минус два") == (5, "-", 2)


def test_compute_all_ops() -> None:
    assert compute(2, "+", 3) == 5
    assert compute(5, "-", 2) == 3
    assert compute(3, "*", 3) == 9
    assert compute(10, "/", 2) == 5
    assert compute(7, "/", 2) == 3.5
    assert compute(5, "/", 0) is None


def test_number_to_ru() -> None:
    assert number_to_ru(5) == "пять"
    assert number_to_ru(9) == "девять"
    assert number_to_ru(21) == "двадцать один"
    assert number_to_ru(-1) == "минус один"


def test_arithmetic_reply() -> None:
    assert arithmetic_reply("Сколько будет два плюс три?") == "Пять."
    assert arithmetic_reply("3*3") == "Девять."
    assert arithmetic_reply("десять минус четыре") == "Шесть."


def test_word_problem_does_not_false_fire() -> None:
    # No operator between the numbers -> must NOT be parsed as arithmetic.
    assert parse_arithmetic("У Маши было 5 яблок, 3 яблока она отдала Васе.") is None
    assert arithmetic_reply("Маша купила апельсин. Что купила Маша?") is None
    assert arithmetic_reply("Как тебя зовут?") is None
