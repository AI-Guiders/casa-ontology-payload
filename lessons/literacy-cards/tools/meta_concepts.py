"""Grammar meta card registry (ADR-0030 L2/L3)."""

from __future__ import annotations

from typing import Any

GRAMMAR_PERSON_CARDS: tuple[dict[str, str], ...] = (
    {"surface": "я", "concept_id": "lang.meta.grammar.person.1sg", "frame_id": "grammar-person-1sg-sans"},
    {"surface": "ты", "concept_id": "lang.meta.grammar.person.2sg", "frame_id": "grammar-person-2sg-sans"},
    {"surface": "он", "concept_id": "lang.meta.grammar.person.3sg.masc", "frame_id": "grammar-person-3sg-masc-sans"},
    {"surface": "она", "concept_id": "lang.meta.grammar.person.3sg.fem", "frame_id": "grammar-person-3sg-fem-sans"},
    {"surface": "мы", "concept_id": "lang.meta.grammar.person.1pl", "frame_id": "grammar-person-1pl-sans"},
    {"surface": "вы", "concept_id": "lang.meta.grammar.person.2pl", "frame_id": "grammar-person-2pl-sans"},
    {"surface": "они", "concept_id": "lang.meta.grammar.person.3pl", "frame_id": "grammar-person-3pl-sans"},
)

GRAMMAR_AGREEMENT_PAIRS: tuple[dict[str, Any], ...] = (
    {
        "concept_id": "lang.meta.grammar.agreement.subjectVerb.fem.sg.past",
        "pairs": (
            {"agent": "мама", "verb": "мыла"},
            {"agent": "сестра", "verb": "мыла"},
        ),
    },
    {
        "concept_id": "lang.meta.grammar.agreement.subjectVerb.masc.sg.past",
        "pairs": (
            {"agent": "брат", "verb": "мыл"},
            {"agent": "папа", "verb": "мыл"},
        ),
    },
)

GRAMMAR_CASE_CARDS: tuple[dict[str, str], ...] = (
    {"surface": "именительный падеж", "concept_id": "lang.meta.grammar.case.nom", "frame_id": "grammar-case-nom-sans"},
    {"surface": "винительный падеж", "concept_id": "lang.meta.grammar.case.acc", "frame_id": "grammar-case-acc-sans"},
)

QUESTION_FRAME_IDS: tuple[str, ...] = (
    "lang.meta.grammar.question.who",
    "lang.meta.grammar.question.what",
    "lang.meta.grammar.question.what_do",
    "lang.meta.grammar.question.which",
    "lang.meta.grammar.question.to_whom",
)
