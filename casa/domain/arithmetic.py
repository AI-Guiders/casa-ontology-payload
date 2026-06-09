#!/usr/bin/env python3
"""Deterministic two-operand arithmetic — parse 'a OP b' (glyph or RU words), compute.

An honest evaluator for the chat: the field's emergent schema path only computes
some products and never plain sums (verified), so a user asking '2+3' would soft-miss.
This fires ONLY on a clean two-operand expression (glyph like '2+3' / '10 / 2', or RU
words like 'два плюс три', 'три умножить на три'), so word problems with no operator
('У Маши было 5 яблок, 3 яблока…') fall through to normal compose untouched.
"""

from __future__ import annotations

import re

_RU_NUM: dict[str, int] = {
    "ноль": 0, "один": 1, "одна": 1, "одно": 1, "два": 2, "две": 2, "три": 3,
    "четыре": 4, "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9,
    "десять": 10, "одиннадцать": 11, "двенадцать": 12, "тринадцать": 13,
    "четырнадцать": 14, "пятнадцать": 15, "шестнадцать": 16, "семнадцать": 17,
    "восемнадцать": 18, "девятнадцать": 19, "двадцать": 20, "тридцать": 30,
    "сорок": 40, "пятьдесят": 50, "шестьдесят": 60, "семьдесят": 70,
    "восемьдесят": 80, "девяносто": 90, "сто": 100,
}

# operator word stems -> canonical op
_OP_STEMS: tuple[tuple[str, str], ...] = (
    ("плюс", "+"), ("прибав", "+"), ("сложить", "+"),
    ("минус", "-"), ("вычес", "-"), ("отними", "-"), ("отнять", "-"),
    ("умнож", "*"), ("помнож", "*"),
    ("раздел", "/"), ("делить", "/"), ("дел", "/"),
)
_GLYPH_OP = {"+": "+", "-": "-", "−": "-", "*": "*", "×": "*", "·": "*", "/": "/", "÷": "/", ":": "/"}

_ONES = ["ноль", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"]
_TEENS = ["десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать", "пятнадцать",
          "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать"]
_TENS = ["", "", "двадцать", "тридцать", "сорок", "пятьдесят", "шестьдесят", "семьдесят",
         "восемьдесят", "девяносто"]


def number_to_ru(n: int | float) -> str:
    """RU cardinal for 0..100 (best effort beyond); non-int rendered as digits."""
    if isinstance(n, float) and not n.is_integer():
        return ("%g" % n).replace(".", ",")
    n = int(n)
    if n < 0:
        return "минус " + number_to_ru(-n)
    if n < 10:
        return _ONES[n]
    if n < 20:
        return _TEENS[n - 10]
    if n < 100:
        o = n % 10
        return _TENS[n // 10] + ((" " + _ONES[o]) if o else "")
    if n == 100:
        return "сто"
    return str(n)


def parse_arithmetic(query: str) -> tuple[int, str, int] | None:
    """Return (a, op, b) for a single two-operand expression, else None."""
    q = (query or "").lower().replace("×", "*").replace("÷", "/").replace("−", "-").replace("·", "*")
    # 1) glyph form: a OP b  (operator symbol required between two integers)
    m = re.search(r"(\d+)\s*([+\-*/:])\s*(\d+)", q)
    if m:
        op = _GLYPH_OP.get(m.group(2))
        if op:
            return int(m.group(1)), op, int(m.group(3))
    # 2) word form: NUM ... OPWORD ... NUM  ('на' filler ignored)
    toks = re.findall(r"[\wЀ-ӿ]+", q)
    nums: list[tuple[int, int]] = []
    op: str | None = None
    op_i = -1
    for i, t in enumerate(toks):
        if t.isdigit():
            nums.append((i, int(t)))
        elif t in _RU_NUM:
            nums.append((i, _RU_NUM[t]))
        elif op is None:
            for stem, o in _OP_STEMS:
                if t.startswith(stem):
                    op, op_i = o, i
                    break
    if op is not None and op_i >= 0:
        before = [v for idx, v in nums if idx < op_i]
        after = [v for idx, v in nums if idx > op_i]
        if before and after:
            return before[-1], op, after[0]
    return None


def compute(a: int, op: str, b: int) -> int | float | None:
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        if b == 0:
            return None
        return a // b if a % b == 0 else round(a / b, 4)
    return None


def arithmetic_reply(query: str) -> str | None:
    """Compute a clean two-operand arithmetic query and articulate it in RU, else None."""
    parsed = parse_arithmetic(query)
    if parsed is None:
        return None
    a, op, b = parsed
    result = compute(a, op, b)
    if result is None:
        return None
    word = number_to_ru(result)
    return word[:1].upper() + word[1:] + "."
