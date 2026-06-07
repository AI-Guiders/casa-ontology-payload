#!/usr/bin/env python3
"""Tract competition model — scores, ids, math/stick parsers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_BOOTSTRAP_TRACT_CLAIMS: list[dict[str, Any]] = [
    {
        "concept_id": "ru.tract.discuss",
        "slots": {
            "requires_geometry": "passage_context",
            "cue_substrings": "позици|автор|почему|зачем|объясни своими|мнение|аргумент|за и против",
            "deny_geometry": "grammar_markers",
        },
    },
    {
        "concept_id": "ru.tract.rewrite",
        "slots": {
            "requires_geometry": "passage_context",
            "cue_substrings": "перепиш|перепис|дружеск|для чата|неформальн|смени тон",
        },
    },
    {
        "concept_id": "ru.tract.explain",
        "slots": {"cue_substrings": "что такое|что означает|объясни|объяснить"},
    },
    {
        "concept_id": "ru.tract.grammar",
        "slots": {"requires_geometry": "grammar_markers"},
    },
    {
        "concept_id": "ru.tract.social",
        "slots": {
            "requires_geometry": "dialogue_turn",
            "deny_geometry": "passage_context",
        },
    },
    {
        "concept_id": "ru.speech_act.rewrite_register",
        "slots": {
            "tract": "rewrite",
            "requires_geometry": "passage_context",
            "cue_substrings": "перепиш|дружеск|сохрани все факты",
        },
    },
]

TRACT_IDS: tuple[str, ...] = (
    "math",
    "discuss",
    "rewrite",
    "explain",
    "grammar",
    "social",
    "general",
)

_CARDINAL_TO_CID = {
    0: "math.num.zero",
    1: "math.num.one",
    2: "math.num.two",
    3: "math.num.three",
    4: "math.num.four",
    5: "math.num.five",
    6: "math.num.six",
    7: "math.num.seven",
    8: "math.num.eight",
    9: "math.num.nine",
    10: "math.num.ten",
}

_OP_GLYPH_TO_CID = {
    "+": "math.op.add",
    "-": "math.op.sub",
    "−": "math.op.sub",
    "×": "math.op.mul",
    "*": "math.op.mul",
    "/": "math.op.div",
    "÷": "math.op.div",
    "=": "math.op.eq",
}


@dataclass
class TractScore:
    tract_id: str
    score: int
    sources: list[str] = field(default_factory=list)


def parse_stick_runs(query: str) -> list[int]:
    return [len(m) for m in re.findall(r"\|+", query)]


def parse_math_ops(query: str) -> list[str]:
    ops: list[str] = []
    for ch in query:
        if ch in _OP_GLYPH_TO_CID and _OP_GLYPH_TO_CID[ch] not in ops:
            ops.append(_OP_GLYPH_TO_CID[ch])
    return ops
