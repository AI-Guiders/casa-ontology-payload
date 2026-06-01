#!/usr/bin/env python3
"""Cardinal abstraction: count×step = repeated addition (skip-count structure), not inventory lookup."""

from __future__ import annotations

import re

_MUL = re.compile(r"^(\d+)\*(\d+)(?:=\?|=\d+)?\??$")


def parse_mul_cue(cue: str) -> tuple[int, int] | None:
    s = str(cue or "").strip().replace(" ", "")
    m = _MUL.match(s)
    return (int(m.group(1)), int(m.group(2))) if m else None


def mul_operator_on_field(decoded: dict, bundle: dict | None = None) -> bool:
    from casa.prisms.memory.f0_stack import _grapheme_for_glyph, concept_in_context

    _ = bundle
    sym = _grapheme_for_glyph("*") or "*"
    return concept_in_context(decoded, sym, "math.ctx.arithmetic") == "math.op.mul"


def abstract_cardinal_magnitude(*, step: int, count: int) -> int:
    """«count предметов по step» — та же абстракция, что счёт рядом / 2+2+2."""
    if step <= 0 or count <= 0:
        return 0
    total = 0
    for _ in range(count):
        total += step
    return total


def cardinality_concept_id(magnitude: int) -> str | None:
    """Мощность N → math.num.*: выученное имя (one…twenty_one) или math.num.N из абстракции счёта."""
    if magnitude < 0:
        return None
    from casa.prisms.memory.f0_pattern_extract import numeral_int_to_concept_id

    return numeral_int_to_concept_id(magnitude) or f"math.num.{magnitude}"


def score_abstract_mul_cue(cue: str, decoded: dict, bundle: dict | None = None) -> dict[str, int]:
    """После *→mul: гипотеза = cardinality результата (не lookup «есть ли N на поле»)."""
    if not mul_operator_on_field(decoded, bundle):
        return {}
    parsed = parse_mul_cue(cue)
    if not parsed:
        return {}
    step, count = parsed
    mag = abstract_cardinal_magnitude(step=step, count=count)
    cid = cardinality_concept_id(mag)
    if not cid:
        return {}
    wants_answer = "?" in cue or re.search(r"=\d", cue.replace(" ", ""))
    return {cid: 52 if wants_answer else 40}
