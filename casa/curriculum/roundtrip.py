#!/usr/bin/env python3
"""Translation through meaning — text -> conceptual graph -> text, with a language switch.

Dmitry's showcase: «перевод с русского на русский». Feed a sentence, the system parses it
into a conceptual graph and renders it BACK into a sentence; same target language gives a
normalised paraphrase («яблоко лежит на столе» -> «Яблоко на столе.»), and flipping the
target language turns the round trip into translation («Apple on the table.»).

It composes the two halves already built: the parser (text -> graph) and a realiser
(graph -> text). The graph is on concepts, so the source language is irrelevant; the
target language is just which surfaces and case rules the realiser uses. Honest scope:
controlled domain clauses; irregular Russian verbs (есть/пить) fall back to the lemma.
"""

from __future__ import annotations

from typing import Any

from casa.curriculum.compose import apply_conditioned_rule
from casa.curriculum.concept_net import names_of
from casa.curriculum.parse import parse_graph

# preposition surface + the Russian case it governs (на/в -> prepositional, у -> genitive)
_LOC_PREP = {
    "on": {"ru": "на", "en": "on", "case": "prep"},
    "in": {"ru": "в", "en": "in", "case": "prep"},
    "near": {"ru": "у", "en": "near", "case": "gen"},
}
_TRANS_VERB = {
    "eat": {"ru": "есть", "en": "eat"},
    "read": {"ru": "читать", "en": "read"},
    "drink": {"ru": "пить", "en": "drink"},
}


def _word(state: dict, lattice_id: str, concept: str, lang: str) -> str:
    nm = names_of(state, lattice_id, concept)
    cand = nm["ru"] if lang == "ru" else nm["en"]
    return cand[0] if cand else concept.split(".")[-1]


def _ru_oblique(state: dict, lattice_id: str, word: str, case: str) -> str:
    """Decline a Russian noun for an oblique case. Genitive picks the rule by gender
    (ending): consonant -> masc, -о/-е -> neuter, -а/-я -> feminine."""
    if case == "gen":
        end = word[-1:]
        rid = (
            "lang.rule.gen-sg-n.ru" if end in "ое"
            else "lang.rule.gen-sg-f.ru" if end in "ая"
            else "lang.rule.gen-sg-m.ru"
        )
    else:
        rid = "lang.rule.prep-sg.ru"
    return apply_conditioned_rule(state, lattice_id, rid, word) or word


def realize_graph(state: dict, lattice_id: str, graph: dict[str, Any], *, lang: str) -> str | None:
    """Render a meaning graph back into a sentence in ``lang`` ('ru'/'en')."""
    from casa.curriculum.clause import compose_full_clause
    from casa.curriculum.sentence import compose_ru_clause

    edges = [(e["rel"], e["src"], e["dst"]) for e in graph.get("edges", []) if e.get("satisfied")]
    if not edges:
        return None

    # locative clause (one figure, a chain of preposition+ground), e.g. on+near
    if all(rel in _LOC_PREP for rel, _, _ in edges):
        first = edges[0]
        fig = _word(state, lattice_id, first[1], lang)
        pieces: list[str] = []
        prev_ground = None
        for rel, src, dst in edges:
            g = _word(state, lattice_id, dst, lang)
            if lang == "ru":
                g = _ru_oblique(state, lattice_id, g, _LOC_PREP[rel]["case"])
                pieces.append(f"{_LOC_PREP[rel]['ru']} {g}")
            else:
                pieces.append(f"{_LOC_PREP[rel]['en']} the {g}")
            prev_ground = dst
        if lang == "ru":
            body = f"{fig} " + " ".join(pieces)
        else:
            body = f"the {fig} is " + " ".join(pieces)
        return body[:1].upper() + body[1:] + "."

    # transitive clause — reuse the bilingual generators (lemmas + relation->verb)
    rel, src, dst = edges[0]
    verb = _TRANS_VERB.get(rel)
    if not verb:
        return None
    if lang == "ru":
        return compose_ru_clause(
            state, lattice_id, subj=_word(state, lattice_id, src, "ru"), verb=verb["ru"], obj=_word(state, lattice_id, dst, "ru")
        )
    return compose_full_clause(
        state, lattice_id,
        subject={"noun": _word(state, lattice_id, src, "en")}, verb=verb["en"],
        obj={"noun": _word(state, lattice_id, dst, "en")}, lang_in="en",
    )


def round_trip(state: dict, lattice_id: str, text: str, *, target: str) -> str | None:
    """Parse ``text`` into a meaning graph and render it back in the ``target`` language.
    Same target = normalised paraphrase; different target = translation through meaning."""
    return realize_graph(state, lattice_id, parse_graph(state, lattice_id, text), lang=target)


def translate_through_meaning(state: dict, lattice_id: str, text: str) -> dict[str, str | None]:
    """Round-trip a sentence into both languages: {'ru': ..., 'en': ...}."""
    g = parse_graph(state, lattice_id, text)
    return {"ru": realize_graph(state, lattice_id, g, lang="ru"), "en": realize_graph(state, lattice_id, g, lang="en")}
