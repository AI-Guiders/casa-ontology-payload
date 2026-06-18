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
# relation -> verb. ``ru3sg`` holds an irregular present 3rd-person-singular as a GIVEN
# lexicon (есть/пить are not covered by the regular -ет rule, which would yield «есет»).
_TRANS_VERB = {
    "eat": {"ru": "есть", "ru3sg": "ест", "en": "eat"},
    "read": {"ru": "читать", "en": "read"},
    "drink": {"ru": "пить", "ru3sg": "пьёт", "en": "drink"},
    # software/UI actions. ``ruimp`` is the Russian (perfective) imperative; ``ruimpneg`` is
    # the imperfective imperative a negative command needs («не закрывай», not «не закрой»).
    # Both are a given lexicon. English imperative is the bare verb (``en``).
    "open": {"ru": "открывать", "ru3sg": "открывает", "ruimp": "открой", "ruimpneg": "открывай", "en": "open"},
    "close": {"ru": "закрывать", "ru3sg": "закрывает", "ruimp": "закрой", "ruimpneg": "закрывай", "en": "close"},
    "save": {"ru": "сохранять", "ru3sg": "сохраняет", "ruimp": "сохрани", "ruimpneg": "сохраняй", "en": "save"},
    "delete": {"ru": "удалять", "ru3sg": "удаляет", "ruimp": "удали", "ruimpneg": "удаляй", "en": "delete"},
    "click": {"ru": "нажимать", "ru3sg": "нажимает", "ruimp": "нажми", "ruimpneg": "нажимай", "en": "click"},
    "select": {"ru": "выбирать", "ru3sg": "выбирает", "ruimp": "выбери", "ruimpneg": "выбирай", "en": "select"},
    "edit": {"ru": "изменять", "ru3sg": "изменяет", "ruimp": "измени", "ruimpneg": "изменяй", "en": "edit"},
}


def _word(state: dict, lattice_id: str, concept: str, lang: str) -> str:
    nm = names_of(state, lattice_id, concept)
    cand = nm["ru"] if lang == "ru" else nm["en"]
    return cand[0] if cand else concept.split(".")[-1]


def _np(state: dict, lattice_id: str, concept: str, lang: str, graph: dict[str, Any]) -> str:
    """Noun phrase for a concept: its adjective attributes (if any) + the noun. Russian
    agrees the adjective with the noun's gender. Use only in nominative positions — the
    locative figure and the transitive subject; oblique agreement is out of scope."""
    from casa.curriculum.attributes import en_adjective, ru_adjective

    noun = _word(state, lattice_id, concept, lang)
    attrs = (graph.get("nodes", {}).get(concept) or {}).get("attrs") or []
    if not attrs:
        return noun
    adjs = [(ru_adjective(a, noun) if lang == "ru" else en_adjective(a)) for a in attrs]
    return " ".join([*adjs, noun])


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
    neg = any(e.get("polarity") == "neg" for e in graph.get("edges", []) if e.get("satisfied"))

    # locative clause (one figure, a chain of preposition+ground), e.g. on+near
    if all(rel in _LOC_PREP for rel, _, _ in edges):
        if neg:
            return None  # negated locative («яблока нет на столе») — handled separately
        first = edges[0]
        fig = _np(state, lattice_id, first[1], lang, graph)
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

    # material clause — «сделан из <material-gen>» / «is made of <material>»
    if len(edges) == 1 and edges[0][0] == "made_of":
        if neg:
            return None  # negated material is out of scope
        _, src, dst = edges[0]
        subj = _np(state, lattice_id, src, lang, graph)
        mat = _word(state, lattice_id, dst, lang)
        if lang == "ru":
            from casa.curriculum.attributes import _gender_of

            made = {"m": "сделан", "n": "сделано", "f": "сделана"}[_gender_of(_word(state, lattice_id, src, "ru"))]
            body = f"{subj} {made} из {_ru_oblique(state, lattice_id, mat, 'gen')}"
        else:
            body = f"the {subj} is made of {mat}"
        return body[:1].upper() + body[1:] + "."

    # transitive clause — reuse the bilingual generators (lemmas + relation->verb)
    rel, src, dst = edges[0]
    verb = _TRANS_VERB.get(rel)
    if not verb:
        return None

    # imperative — subject is the implicit «you»: «Открой файл.» / «Не закрывай окно.»
    if src == "lex.you":
        obj = _word(state, lattice_id, dst, lang)
        if lang == "ru":
            from casa.curriculum.sentence import RU_ACC_RULE

            obj_acc = apply_conditioned_rule(state, lattice_id, RU_ACC_RULE, obj) or obj
            # a negative command takes the imperfective imperative («не закрывай», not «закрой»)
            form = verb.get("ruimpneg", verb.get("ru", "")) if neg else verb.get("ruimp", verb["ru"])
            body = f"не {form} {obj_acc}" if neg else f"{form} {obj_acc}"
        else:
            body = f"do not {verb['en']} the {obj}" if neg else f"{verb['en']} the {obj}"
        return body[:1].upper() + body[1:] + "."

    if lang == "ru":
        v3 = verb.get("ru3sg") or apply_conditioned_rule(state, lattice_id, "lang.rule.present3sg.ru", verb["ru"]) or verb["ru"]
        return compose_ru_clause(
            state, lattice_id, subj=_np(state, lattice_id, src, "ru", graph), verb=verb["ru"],
            obj=_word(state, lattice_id, dst, "ru"), verb_form=(f"не {v3}" if neg else verb.get("ru3sg")),
        )
    return compose_full_clause(
        state, lattice_id,
        subject={"noun": _np(state, lattice_id, src, "en", graph)}, verb=verb["en"],
        obj={"noun": _word(state, lattice_id, dst, "en")}, lang_in="en",
        polarity=("negative" if neg else "affirmative"),
    )


def round_trip(state: dict, lattice_id: str, text: str, *, target: str) -> str | None:
    """Parse ``text`` into a meaning graph and render it back in the ``target`` language.
    Same target = normalised paraphrase; different target = translation through meaning."""
    return realize_graph(state, lattice_id, parse_graph(state, lattice_id, text), lang=target)


def translate_through_meaning(state: dict, lattice_id: str, text: str) -> dict[str, str | None]:
    """Round-trip a sentence into both languages: {'ru': ..., 'en': ...}."""
    g = parse_graph(state, lattice_id, text)
    return {"ru": realize_graph(state, lattice_id, g, lang="ru"), "en": realize_graph(state, lattice_id, g, lang="en")}
