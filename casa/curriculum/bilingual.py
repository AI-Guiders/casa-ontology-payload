#!/usr/bin/env python3
"""Bilingual clause — one meaning triple, the same sentence in BOTH languages.

This is the capstone of the language track: it translates the MEANING (a role-tagged
subject/verb/object triple) and renders it in each grammar — the glossary maps the
lemmas across languages, then the English and Russian generators inflect and order
independently:

    {девочка, читать, книга}  ->  RU «Девочка читает книгу.»
                                  EN  "The girl reads the book."

Honest ceiling (same as the generators): it translates a GIVEN meaning triple, it does
not PARSE a free sentence into roles — role assignment is understanding, which the
substrate does not do. Coverage is bounded by the glossary and the morphology rules;
unknown words / unsupported forms decline (None) rather than invent.
"""

from __future__ import annotations

from typing import Any

from casa.curriculum.clause import compose_full_clause
from casa.curriculum.sentence import compose_ru_clause
from casa.curriculum.translate import translate_term


def _to(state: dict, lattice_id: str, word: str, target: str) -> str | None:
    hits = translate_term(state, lattice_id, word, to_script="latn" if target == "en" else "cyrl")
    return hits[0] if hits else None


def bilingual_clause(
    state: dict,
    lattice_id: str,
    *,
    subj: str,
    verb: str,
    obj: str,
    source: str = "ru",
    tense: str = "present",
    polarity: str = "affirmative",
    mood: str = "declarative",
    irregular_past: dict[str, str] | None = None,
) -> dict[str, str | None]:
    """Render one meaning triple (lemmas in ``source``) as a clause in both languages.

    Returns ``{"ru": ..., "en": ...}``; a side is None if a word is unknown to the
    glossary or a grammar rule/order is missing. English grammatical features
    (tense/polarity/mood) apply to the English side."""
    def triple(target: str) -> tuple[str | None, str | None, str | None]:
        if source == target:
            return subj, verb, obj
        return tuple(_to(state, lattice_id, w, target) for w in (subj, verb, obj))  # type: ignore[return-value]

    ru = triple("ru")
    en = triple("en")
    ru_sent = compose_ru_clause(state, lattice_id, subj=ru[0], verb=ru[1], obj=ru[2]) if all(ru) else None
    en_sent = (
        compose_full_clause(
            state,
            lattice_id,
            subject={"noun": en[0]},
            obj={"noun": en[2]},
            verb=en[1],
            lang_in="en",
            tense=tense,
            polarity=polarity,
            mood=mood,
            irregular_past=irregular_past,
        )
        if all(en)
        else None
    )
    return {"ru": ru_sent, "en": en_sent}


def translate_clause(
    state: dict, lattice_id: str, *, subj: str, verb: str, obj: str, source: str, target: str, **kw: Any
) -> str | None:
    """Translate a meaning triple from ``source`` and render it in ``target``."""
    return bilingual_clause(state, lattice_id, subj=subj, verb=verb, obj=obj, source=source, **kw).get(target)


def gate_bilingual(
    state: dict,
    lattice_id: str,
    cases: list[tuple[dict[str, str], str, str]],
    *,
    pass_ratio: float = 0.9,
) -> dict[str, Any]:
    """Verify held-out triples render correctly in BOTH languages, and that ablating
    the clause templates (RU S-V-O + EN declarative order) collapses production.

    Each case is ``(triple, expected_ru, expected_en)`` where ``triple`` carries
    ``subj/verb/obj`` and ``source``. The glossary + morphology + order rules must be
    taught into ``state`` already."""
    from casa.prisms.memory.f0_stack import weaken_graph_edge
    from casa.prisms.memory.memory_prisms import memory_lattices

    def render(triple: dict[str, str]) -> dict[str, str | None]:
        return bilingual_clause(state, lattice_id, **triple)

    both = [
        render(t)["ru"] == ru and render(t)["en"] == en for t, ru, en in cases
    ]
    pass_rate = sum(both) / len(both) if both else 0.0

    lats = memory_lattices(state)
    for i, slot in enumerate(["subj", "verb", "obj"]):
        weaken_graph_edge(lats, lattice_id, "lang.sentence.svo.ru", "order", f"lang.slot.{slot}@{i}")
    for i, slot in enumerate(["subj", "vfin", "obj"]):
        weaken_graph_edge(lats, lattice_id, "lang.clause.decl.en", "order", f"lang.slot.{slot}@{i}")
    ablation_breaks = all(render(t)["ru"] is None and render(t)["en"] is None for t, _, _ in cases)

    passed = bool(len(cases) >= 3 and pass_rate >= pass_ratio and ablation_breaks)
    return {
        "passed": passed,
        "cases": len(cases),
        "both_languages_pass_rate": round(pass_rate, 3),
        "ablation_breaks_production": ablation_breaks,
    }
