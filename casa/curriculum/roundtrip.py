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
    "wear": {"ru": "носить", "ru3sg": "носит", "ruimp": "надень", "ruimpneg": "носи", "en": "wear"},
    "use": {"ru": "использовать", "ru3sg": "использует", "ruimp": "используй", "ruimpneg": "используй", "en": "use"},
    "write": {"ru": "писать", "ru3sg": "пишет", "ruimp": "напиши", "ruimpneg": "пиши", "en": "write"},
    "cook": {"ru": "готовить", "ru3sg": "готовит", "ruimp": "приготовь", "ruimpneg": "готовь", "en": "cook"},
    "wash": {"ru": "мыть", "ru3sg": "моет", "ruimp": "помой", "ruimpneg": "мой", "en": "wash"},
    "give": {"ru": "давать", "ru3sg": "даёт", "ruimp": "дай", "ruimpneg": "давай", "en": "give"},
    "take": {"ru": "брать", "ru3sg": "берёт", "ruimp": "возьми", "ruimpneg": "бери", "en": "take"},
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
    "show": {"ru": "показывать", "ru3sg": "показывает", "ruimp": "покажи", "ruimpneg": "показывай", "en": "show"},
    "configure": {"ru": "настраивать", "ru3sg": "настраивает", "ruimp": "настрой", "ruimpneg": "настраивай", "en": "configure"},
    "copy": {"ru": "копировать", "ru3sg": "копирует", "ruimp": "скопируй", "ruimpneg": "копируй", "en": "copy"},
    "move": {"ru": "перемещать", "ru3sg": "перемещает", "ruimp": "перемести", "ruimpneg": "перемещай", "en": "move"},
    "create": {"ru": "создавать", "ru3sg": "создаёт", "ruimp": "создай", "ruimpneg": "создавай", "en": "create"},
    "rename": {"ru": "переименовывать", "ru3sg": "переименовывает", "ruimp": "переименуй", "ruimpneg": "переименовывай", "en": "rename"},
    "print": {"ru": "печатать", "ru3sg": "печатает", "ruimp": "распечатай", "ruimpneg": "печатай", "en": "print"},
    "enable": {"ru": "включать", "ru3sg": "включает", "ruimp": "включи", "ruimpneg": "включай", "en": "enable"},
    "install": {"ru": "устанавливать", "ru3sg": "устанавливает", "ruimp": "установи", "ruimpneg": "устанавливай", "en": "install"},
    "download": {"ru": "скачивать", "ru3sg": "скачивает", "ruimp": "скачай", "ruimpneg": "скачивай", "en": "download"},
}


def _word(state: dict, lattice_id: str, concept: str, lang: str) -> str:
    nm = names_of(state, lattice_id, concept)
    cand = nm["ru"] if lang == "ru" else nm["en"]
    return cand[0] if cand else concept.split(".")[-1]


def _np(state: dict, lattice_id: str, concept: str, lang: str, graph: dict[str, Any]) -> str:
    """Noun phrase for a concept: count + adjective attributes + the noun. A count governs
    the noun's case (1 → nominative, 2-4 → genitive singular; 5+ approximated). Russian
    agrees the adjective with the noun's gender. Nominative-position use (figure/subject)."""
    from casa.curriculum.attributes import _gender_of, en_adjective, ru_adjective
    from casa.curriculum.quantity import en_number_word, ru_noun_case, ru_number_word, unit_surface

    node = graph.get("nodes", {}).get(concept) or {}
    noun = _word(state, lattice_id, concept, lang)
    attrs = node.get("attrs") or []
    count = node.get("count")
    measure = node.get("measure")
    if measure:  # «5 мл воды» / «5 ml of water» — value + unit + partitive noun
        unit = unit_surface(measure["unit"], lang)
        if lang == "ru":
            return f"{measure['value']} {unit} {_ru_oblique(state, lattice_id, noun, 'gen')}"
        return f"{measure['value']} {unit} of {noun}"
    if lang == "ru":
        adjs = [ru_adjective(a, noun) for a in attrs]
        if count:
            form = noun if ru_noun_case(count) == "nom" else _ru_oblique(state, lattice_id, noun, "gen")
            return " ".join([ru_number_word(count, _gender_of(noun)), *adjs, form])
        return " ".join([*adjs, noun])
    adjs = [en_adjective(a) for a in attrs]
    if count:
        form = noun if count == 1 else (apply_conditioned_rule(state, lattice_id, "lang.rule.plural.en", noun) or f"{noun}s")
        return " ".join([en_number_word(count), *adjs, form])
    return " ".join([*adjs, noun])


def _obj(state: dict, lattice_id: str, concept: str, lang: str, graph: dict[str, Any]) -> str:
    """Render an object. A counted/measured object follows the numeral's case («удали два
    файла», «выпей 5 мл воды»); an uncounted Russian object goes to the accusative."""
    node = graph.get("nodes", {}).get(concept) or {}
    if node.get("count") or node.get("measure"):
        return _np(state, lattice_id, concept, lang, graph)
    word = _word(state, lattice_id, concept, lang)
    if lang == "ru":
        from casa.curriculum.sentence import RU_ACC_RULE

        return apply_conditioned_rule(state, lattice_id, RU_ACC_RULE, word) or word
    return word


def _ru_oblique(state: dict, lattice_id: str, word: str, case: str) -> str:
    """Decline a Russian noun for an oblique case. Genitive picks the rule by gender
    (ending): consonant -> masc, -о/-е -> neuter, -а/-я -> feminine."""
    if case == "gen":
        if word.endswith("ь"):
            return word[:-1] + "и"  # soft-sign feminine genitive: мышь→мыши, дверь→двери
        end = word[-1:]
        rid = (
            "lang.rule.gen-sg-n.ru" if end in "ое"
            else "lang.rule.gen-sg-f.ru" if end in "ая"
            else "lang.rule.gen-sg-m.ru"
        )
    else:
        rid = "lang.rule.prep-sg.ru"
    return apply_conditioned_rule(state, lattice_id, rid, word) or word


def _is_chain(edges: list[tuple[str, str, str]]) -> bool:
    """True if the edges form one simple path (a─▶b─▶c) — a nested locative, not coordination
    («яблоко на столе у окна»); False for coordinated figures/objects (a repeated src/dst)."""
    srcs = [s for _, s, _ in edges]
    dsts = [d for _, _, d in edges]
    if len(set(srcs)) != len(srcs):
        return False  # two edges share a source -> coordinated, not a chain
    starts = [s for s in srcs if s not in dsts]
    return len(starts) == 1


def _subgraph(graph: dict[str, Any], edge: tuple[str, str, str]) -> dict[str, Any]:
    """A one-edge graph (edge dict + its two nodes) for realizing a single conjunct."""
    rel, src, dst = edge
    e = next(x for x in graph["edges"]
             if x.get("satisfied") and (x["rel"], x["src"], x["dst"]) == (rel, src, dst))
    nodes = graph.get("nodes", {})
    return {"nodes": {src: nodes.get(src, {}), dst: nodes.get(dst, {})}, "edges": [e]}


def _en_det(graph: dict[str, Any], cid: str) -> str:
    node = graph.get("nodes", {}).get(cid) or {}
    return "" if (node.get("count") or node.get("measure")) else "the "


def _realize_action_dest(state: dict, lattice_id: str, graph: dict[str, Any],
                         act: tuple[str, str, str], dst_e: tuple[str, str, str], *, lang: str) -> str | None:
    """Render an action with a destination: «Сохрани файл в папку.» / «Save the file to the
    folder.» — the action clause + the goal («в» + accusative in RU, «to the» in EN)."""
    head = realize_graph(state, lattice_id, _subgraph(graph, act), lang=lang)
    if not head:
        return None
    head = head.rstrip(".")
    prel, _, dest = dst_e
    dest_word = _word(state, lattice_id, dest, lang)
    if lang == "ru":
        from casa.curriculum.sentence import RU_ACC_RULE

        prep = _LOC_PREP.get(prel, {}).get("ru", "в")
        dest_acc = apply_conditioned_rule(state, lattice_id, RU_ACC_RULE, dest_word) or dest_word
        return f"{head} {prep} {dest_acc}."
    return f"{head} to the {dest_word}."


def _realize_coordination(state: dict, lattice_id: str, graph: dict[str, Any],
                          edges: list[tuple[str, str, str]], *, lang: str) -> str | None:
    """Render coordinated edges, joined by «и»/«and», factoring a shared element where it
    reads cleanly (one verb / one subject / one location)."""
    conj = "и" if lang == "ru" else "and"
    rels = {r for r, _, _ in edges}
    srcs = {s for _, s, _ in edges}
    dsts = {d for _, _, d in edges}

    def cap(body: str) -> str:
        return body[:1].upper() + body[1:] + "."

    # coordinated figures of one location: «Яблоко и книга на столе.»
    if len(rels) == 1 and len(dsts) == 1 and edges[0][0] in _LOC_PREP:
        rel, _, ground = edges[0]
        spec = _LOC_PREP[rel]
        figs = [_np(state, lattice_id, s, lang, graph) for _, s, _ in edges]
        gword = _word(state, lattice_id, ground, lang)
        if lang == "ru":
            return cap(f"{f' {conj} '.join(figs)} {spec['ru']} {_ru_oblique(state, lattice_id, gword, spec['case'])}")
        figs_the = [f"the {f}" for f in figs]
        return cap(f"{f' {conj} '.join(figs_the)} are {spec['en']} the {gword}")

    # coordinated objects of one action: «Удали файл и папку.»
    if len(rels) == 1 and len(srcs) == 1 and edges[0][0] in _TRANS_VERB:
        head = realize_graph(state, lattice_id, _subgraph(graph, edges[0]), lang=lang)
        if not head:
            return None
        head = head.rstrip(".")
        for _, _, dst in edges[1:]:
            obj = _obj(state, lattice_id, dst, lang, graph)
            head += f" {conj} {obj}" if lang == "ru" else f" {conj} {_en_det(graph, dst)}{obj}"
        return head + "."

    # one subject, several predicates: «Собака ест мясо и пьёт молоко.» (subject once)
    if len(srcs) == 1 and edges[0][1] != "concept.you" and all(r in _TRANS_VERB for r, _, _ in edges):
        head = realize_graph(state, lattice_id, _subgraph(graph, edges[0]), lang=lang)
        if head:
            head = head.rstrip(".")
            for rel, _, dst in edges[1:]:
                verb = _TRANS_VERB[rel]
                obj = _obj(state, lattice_id, dst, lang, graph)
                if lang == "ru":
                    v3 = verb.get("ru3sg") or apply_conditioned_rule(state, lattice_id, "lang.rule.present3sg.ru", verb["ru"]) or verb["ru"]
                    head += f" {conj} {v3} {obj}"
                else:
                    v3 = apply_conditioned_rule(state, lattice_id, "lang.rule.present3sg.en", verb["en"]) or f"{verb['en']}s"
                    head += f" {conj} {v3} {_en_det(graph, dst)}{obj}"
            return head + "."

    # general: realize each conjunct as its own clause and join
    parts = [realize_graph(state, lattice_id, _subgraph(graph, e), lang=lang) for e in edges]
    parts = [p.rstrip(".") for p in parts if p]
    if not parts:
        return None
    return cap(parts[0] + "".join(f" {conj} {p[:1].lower() + p[1:]}" for p in parts[1:]))


def realize_graph(state: dict, lattice_id: str, graph: dict[str, Any], *, lang: str) -> str | None:
    """Render a meaning graph back into a sentence in ``lang`` ('ru'/'en')."""
    from casa.curriculum.clause import compose_full_clause
    from casa.curriculum.sentence import compose_ru_clause

    edges = [(e["rel"], e["src"], e["dst"]) for e in graph.get("edges", []) if e.get("satisfied")]
    if not edges:
        return None
    neg = any(e.get("polarity") == "neg" for e in graph.get("edges", []) if e.get("satisfied"))

    # action with a destination: «сохрани файл в папку» — an action edge plus a locative edge
    # on its object («save»: in(file, folder)) → «<action> <prep> <destination>»
    if len(edges) == 2:
        act = next((e for e in edges if e[0] in _TRANS_VERB), None)
        dst_e = next((e for e in edges if e[0] in _LOC_PREP), None)
        if act and dst_e and dst_e[1] == act[2]:
            return _realize_action_dest(state, lattice_id, graph, act, dst_e, lang=lang)

    # coordination — several edges that are not one locative chain («открой файл и сохрани
    # документ», «удали файл и папку», «яблоко и книга на столе»)
    if len(edges) > 1 and not _is_chain(edges):
        return _realize_coordination(state, lattice_id, graph, edges, lang=lang)

    # locative clause (one figure, a chain of preposition+ground), e.g. on+near
    if all(rel in _LOC_PREP for rel, _, _ in edges):
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
        fig_node = graph.get("nodes", {}).get(first[1]) or {}
        fig_count = fig_node.get("count")
        if lang == "ru":
            body = f"{fig} {'не ' if neg else ''}" + " ".join(pieces)  # «Яблоко не на столе.»
        else:
            det = "" if (fig_count or fig_node.get("measure")) else "the "
            cop = "are" if fig_count and fig_count != 1 else "is"
            body = f"{det}{fig} {cop} {'not ' if neg else ''}" + " ".join(pieces)
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

    # colour predicate — «Яблоко красное.» / «The apple is red.»
    if len(edges) == 1 and edges[0][0] == "color_of":
        from casa.curriculum.attributes import en_adjective, ru_adjective

        _, src, dst = edges[0]
        color = dst.split(".")[-1]  # concept.red -> red
        noun = _word(state, lattice_id, src, lang)
        if lang == "ru":
            body = f"{noun} {'не ' if neg else ''}{ru_adjective(color, noun)}"
        else:
            body = f"the {noun} is {'not ' if neg else ''}{en_adjective(color)}"
        return body[:1].upper() + body[1:] + "."

    # comparison — «Слон больше мыши.» / «The elephant is bigger than the mouse.»
    if len(edges) == 1 and edges[0][0] == "bigger_than":
        _, src, dst = edges[0]
        x = _word(state, lattice_id, src, lang)
        y = _word(state, lattice_id, dst, lang)
        if lang == "ru":
            body = f"{x} {'не ' if neg else ''}больше {_ru_oblique(state, lattice_id, y, 'gen')}"
        else:
            body = f"the {x} is {'not ' if neg else ''}bigger than the {y}"
        return body[:1].upper() + body[1:] + "."

    # habitat — «Кошка живёт в доме.» / «The cat lives in the house.»
    if len(edges) == 1 and edges[0][0] == "lives_in":
        _, src, dst = edges[0]
        x = _word(state, lattice_id, src, lang)
        h = _word(state, lattice_id, dst, lang)
        if lang == "ru":
            body = f"{x} {'не ' if neg else ''}живёт в {_ru_oblique(state, lattice_id, h, 'prep')}"
        else:
            body = f"the {x} {'does not live' if neg else 'lives'} in the {h}"
        return body[:1].upper() + body[1:] + "."

    # transitive clause — reuse the bilingual generators (lemmas + relation->verb)
    rel, src, dst = edges[0]
    verb = _TRANS_VERB.get(rel)
    if not verb:
        return None

    dst_node = graph.get("nodes", {}).get(dst) or {}
    quantified = bool(dst_node.get("count") or dst_node.get("measure"))  # numeral governs case

    # imperative — subject is the implicit «you»: «Открой файл.» / «Удали два файла.»
    if src == "concept.you":
        obj = _obj(state, lattice_id, dst, lang, graph)
        if lang == "ru":
            # a negative command takes the imperfective imperative («не закрывай», not «закрой»)
            form = verb.get("ruimpneg", verb.get("ru", "")) if neg else verb.get("ruimp", verb["ru"])
            body = f"не {form} {obj}" if neg else f"{form} {obj}"
        else:
            det = "" if quantified else "the "  # «Delete two files» (no article when quantified)
            body = f"do not {verb['en']} {det}{obj}" if neg else f"{verb['en']} {det}{obj}"
        return body[:1].upper() + body[1:] + "."

    if lang == "ru":
        v3 = verb.get("ru3sg") or apply_conditioned_rule(state, lattice_id, "lang.rule.present3sg.ru", verb["ru"]) or verb["ru"]
        return compose_ru_clause(
            state, lattice_id, subj=_np(state, lattice_id, src, "ru", graph), verb=verb["ru"],
            obj=_word(state, lattice_id, dst, "ru"), verb_form=(f"не {v3}" if neg else verb.get("ru3sg")),
            obj_form=(_np(state, lattice_id, dst, "ru", graph) if quantified else None),
        )
    obj_spec: dict[str, Any] = {"noun": _word(state, lattice_id, dst, "en")}
    if dst_node.get("count"):  # English plural NP for a plain count (measures use _obj path)
        from casa.curriculum.quantity import en_number_word

        obj_spec = {"noun": _word(state, lattice_id, dst, "en"),
                    "number": en_number_word(dst_node["count"]), "determiner": ""}
    return compose_full_clause(
        state, lattice_id,
        subject={"noun": _np(state, lattice_id, src, "en", graph)}, verb=verb["en"],
        obj=obj_spec, lang_in="en",
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
