#!/usr/bin/env python3
"""Questions to the conceptual network — a query is a partial graph with a variable.

This closes the dialogue loop: you state a situation, then ASK about it, and the answer
comes from the graph (memory + ontology), not the statistical engine. Three question
shapes, each answered deterministically and auditably:

  location   «что на столе?» / «где яблоко?»   — a relation edge with one slot unbound;
             scan remembered situations for the matching figure / ground.
  affordance «съедобно ли яблоко?» / «можно ли пить воду?» — does the concept's type
             afford the capability? pure ontology (isa-closure of affordances).
  material   «из чего стол?»                    — needs made_of facts the ontology does
             not carry yet; answered honestly with «не знаю».

Anything that is not a recognised question returns None, so the caller falls through to
the normal dialogue path. Honest scope: controlled question forms over known concepts.
"""

from __future__ import annotations

import re
from typing import Any

# adjective-predicate question stems -> the affordance they probe («съедобно» -> edible)
_ADJ_AFFORD = {
    "съедобн": "edible", "питьев": "drinkable", "читаем": "readable",
    "носим": "wearable", "edible": "edible", "drinkable": "drinkable",
}
# affordance -> infinitive, for a gender/case-free answer («можно есть» / «нельзя пить»)
_AFFORD_VERB = {
    "edible": "есть", "drinkable": "пить", "readable": "читать", "wearable": "носить",
    "openable": "открыть", "savable": "сохранить", "deletable": "удалить",
    "closable": "закрыть", "clickable": "нажать", "selectable": "выбрать", "editable": "изменить",
}
_QUESTION_LEADS = ("что", "где", "из чего", "съедобн", "можно", "what", "where")


def _tokens(text: str) -> list[str]:
    return re.findall(r"[\wЀ-ӿ]+", str(text or "").lower(), flags=re.UNICODE)


def looks_question(text: str) -> bool:
    """Cheap check (no network): a short line that ends in '?' or opens like a question."""
    t = text.strip().lower()
    return bool(t) and (t.endswith("?") or t.startswith(_QUESTION_LEADS))


def _ru_name(state: dict, lattice_id: str, concept: str) -> str:
    from casa.curriculum.concept_net import names_of

    base = re.split(r"[\[×{]", concept)[0]  # strip a node token's attrs/count/measure annotations
    ru = names_of(state, lattice_id, base)["ru"]
    return ru[0] if ru else base.split(".")[-1]


def _edge_re(rel: str | None, src: str | None, dst: str | None) -> re.Pattern[str]:
    """Match a canonical edge key ``rel(src,dst)`` with None meaning 'any'."""
    r = re.escape(rel) if rel else r"[^()]+"
    s = re.escape(src) if src else r"[^,()]+"
    d = re.escape(dst) if dst else r"[^,()]+"
    return re.compile(rf"^{r}\({s},{d}\)$")


def _scan_memory(state: dict, lattice_id: str, pattern: re.Pattern[str], group_concept: int) -> list[str]:
    """Concepts captured from remembered edges matching ``pattern`` (figure or ground)."""
    from casa.curriculum.situation_store import load_memory

    found: list[str] = []
    for rec in load_memory(state, lattice_id)["situations"]:
        for edge in rec["edges"]:
            m = re.match(r"^([^()]+)\(([^,()]+),([^,()]+)\)$", edge)
            if m and pattern.match(edge):
                cid = m.group(group_concept)
                if cid not in found:
                    found.append(cid)
    return found


def _ru_locative(state: dict, lattice_id: str, rel: str, ground: str) -> str:
    """«на столе» / «в коробке» / «у окна» — preposition + the ground in its case."""
    from casa.curriculum.roundtrip import _LOC_PREP, _ru_oblique

    spec = _LOC_PREP.get(rel)
    gname = _ru_name(state, lattice_id, ground)
    if not spec:
        return gname
    return f"{spec['ru']} {_ru_oblique(state, lattice_id, gname, spec['case'])}"


def _answer_location(state: dict, lattice_id: str, toks: list[str]) -> str | None:
    """«что на/в/у X?» (figures at a ground) and «где X?» (the ground of a figure)."""
    from casa.curriculum.concept_net import concept_of
    from casa.curriculum.parse import _name_index, resolve_token
    from casa.curriculum.situation import PREDICATE_RELATION, normalize_relation

    names = _name_index(state, lattice_id)

    def resolve(tok: str) -> str | None:
        if tok in PREDICATE_RELATION:  # «на»/«в» are relations here, not concepts
            return None
        return concept_of(state, lattice_id, tok) or resolve_token(state, lattice_id, tok, names)

    # «что <prep> <ground>?» — unbound figure
    if toks[0] in ("что", "what"):
        rel = next((normalize_relation(t) for t in toks if t in PREDICATE_RELATION), None)
        grounds = [c for t in toks if (c := resolve(t))]
        if rel and grounds:
            ground = grounds[-1]
            figs = _scan_memory(state, lattice_id, _edge_re(rel, None, ground), 2)
            loc = _ru_locative(state, lattice_id, rel, ground)
            if figs:
                names_ru = ", ".join(_ru_name(state, lattice_id, f) for f in figs)
                return f"{loc[:1].upper() + loc[1:]}: {names_ru}."
            return f"Про «{_ru_name(state, lattice_id, ground)}» я ничего не помню."

    # «где <figure>?» / «где живёт <figure>?» — unbound ground+relation
    if toks[0] in ("где", "where"):
        figs = [c for t in toks[1:] if (c := resolve(t))]
        if figs:
            figure = figs[0]
            edges = _scan_memory_full(state, lattice_id, _edge_re(None, figure, None))
            fname = _ru_name(state, lattice_id, figure)
            cap = fname[:1].upper() + fname[1:]
            habitat = "живёт" in toks or "lives" in toks  # «где живёт X?» asks about the home
            live_edges = [e for e in edges if e[0] == "lives_in"]
            if habitat and live_edges:
                from casa.curriculum.roundtrip import _ru_oblique

                dst = live_edges[0][2]
                return f"{cap} живёт в {_ru_oblique(state, lattice_id, _ru_name(state, lattice_id, dst), 'prep')}."
            if edges:
                rel, _, dst = edges[0]
                if rel == "lives_in":
                    from casa.curriculum.roundtrip import _ru_oblique

                    return f"{cap} живёт в {_ru_oblique(state, lattice_id, _ru_name(state, lattice_id, dst), 'prep')}."
                return f"{cap} {_ru_locative(state, lattice_id, rel, dst)}."
            return f"Где «{fname}» — я не помню."
    return None


def _scan_memory_full(state: dict, lattice_id: str, pattern: re.Pattern[str]) -> list[tuple[str, str, str]]:
    """Remembered edges matching ``pattern`` as (rel, src, dst) tuples."""
    from casa.curriculum.situation_store import load_memory

    out: list[tuple[str, str, str]] = []
    for rec in load_memory(state, lattice_id)["situations"]:
        for edge in rec["edges"]:
            m = re.match(r"^([^()]+)\(([^,()]+),([^,()]+)\)$", edge)
            if m and pattern.match(edge):
                out.append((m.group(1), m.group(2), m.group(3)))
    return out


def _color_attr_from_memory(state: dict, lattice_id: str, target: str) -> str | None:
    """A colour adjective attribute on ``target`` in any remembered edge (concept.apple[red])."""
    from casa.curriculum.attributes import COLOR_IDS
    from casa.curriculum.situation_store import load_memory

    for rec in load_memory(state, lattice_id)["situations"]:
        for edge in rec["edges"]:
            for m in re.finditer(rf"{re.escape(target)}\[([^\]]+)\]", edge):
                for a in m.group(1).split(","):
                    if a in COLOR_IDS:
                        return a
    return None


def _answer_color(state: dict, lattice_id: str, toks: list[str]) -> str | None:
    """«какого цвета X?» — recall a stated colour (color_of edge) or a colour attribute."""
    if not (any(t.startswith("цвет") for t in toks) or "color" in toks or "colour" in toks):
        return None
    from casa.curriculum.attributes import ru_adjective
    from casa.curriculum.concept_net import concept_of
    from casa.curriculum.parse import _name_index, resolve_token

    names = _name_index(state, lattice_id)
    skip = {"какого", "цвета", "цвет", "какой", "what", "color", "colour", "is", "the", "of"}
    targets = [c for t in toks if t not in skip
               and (c := (concept_of(state, lattice_id, t) or resolve_token(state, lattice_id, t, names)))]
    if not targets:
        return None
    target = targets[-1]
    edges = _scan_memory_full(state, lattice_id, _edge_re("color_of", target, None))
    color = edges[0][2].split(".")[-1] if edges else _color_attr_from_memory(state, lattice_id, target)
    name = _ru_name(state, lattice_id, target)
    if color:
        return f"{name[:1].upper() + name[1:]} {ru_adjective(color, name)}."
    return f"Не знаю, какого цвета «{name}»."


def _answer_comparison(state: dict, lattice_id: str, toks: list[str]) -> str | None:
    """«слон больше мыши?» — yes/no over the bigger_than graph, with transitive inference
    («слон больше мыши» + «мышь больше муравья» ⊢ «слон больше муравья»)."""
    if not ("больше" in toks or "bigger" in toks):
        return None
    from casa.curriculum.concept_net import concept_of
    from casa.curriculum.parse import _name_index, resolve_token

    names = _name_index(state, lattice_id)
    skip = {"больше", "bigger", "than", "чем", "ли", "что", "кто", "what", "who", "is", "the", "или", "or"}
    nouns = [c for t in toks if t.strip("?.,!") not in skip
             and (c := (concept_of(state, lattice_id, t) or resolve_token(state, lattice_id, t, names)))]
    if len(nouns) < 2:
        return None
    x, y = nouns[0], nouns[1]
    pairs = {(s, d) for _, s, d in _scan_memory_full(state, lattice_id, _edge_re("bigger_than", None, None))}

    def reaches(start: str, goal: str) -> bool:  # transitive closure of bigger_than
        seen, frontier = set(), [start]
        while frontier:
            cur = frontier.pop()
            for s, d in pairs:
                if s == cur and d not in seen:
                    if d == goal:
                        return True
                    seen.add(d)
                    frontier.append(d)
        return False

    xn, yn = _ru_name(state, lattice_id, x), _ru_name(state, lattice_id, y)
    if reaches(x, y):
        return f"Да, «{xn}» больше «{yn}»."
    if reaches(y, x):
        return f"Нет, наоборот: «{yn}» больше «{xn}»."
    return f"Не знаю, больше ли «{xn}», чем «{yn}»."


def _answer_affordance(state: dict, lattice_id: str, toks: list[str]) -> str | None:
    """«съедобно ли X?» / «можно ли <verb> X?» — does X's type afford the capability?"""
    from casa.curriculum.concept_net import affordances_of, concept_of, relation_roles
    from casa.curriculum.parse import _name_index, resolve_token
    from casa.curriculum.situation import PREDICATE_RELATION, normalize_relation

    names = _name_index(state, lattice_id)

    def resolve(tok: str) -> str | None:
        return concept_of(state, lattice_id, tok) or resolve_token(state, lattice_id, tok, names)

    need: str | None = None
    # adjective-predicate: «съедобно/съедобен ли …»
    for t in toks:
        for stem, afford in _ADJ_AFFORD.items():
            if t.startswith(stem):
                need = afford
                break
        if need:
            break
    # verb form: «можно ли <verb> …» -> the verb's object affordance (eat -> edible)
    if need is None and ("можно" in toks or "can" in toks):
        rel = next((normalize_relation(t) for t in toks if t in PREDICATE_RELATION), None)
        if rel:
            need = relation_roles(state, lattice_id, rel)[1]
    if need is None:
        return None

    targets = [c for t in toks if (c := resolve(t))]
    if not targets:
        return None
    target = targets[-1]
    name = _ru_name(state, lattice_id, target)
    verb = _AFFORD_VERB.get(need, need)
    if need in affordances_of(state, lattice_id, target):
        return f"Да — «{name}» можно {verb} (по типу это {need})."
    return f"Нет — «{name}» нельзя {verb}."


def _answer_material(state: dict, lattice_id: str, toks: list[str]) -> str | None:
    """«из чего X?» — recall a remembered made_of(X, material) fact, else answer honestly."""
    if not ("из" in toks and ("чего" in toks or "что" in toks)):
        return None
    from casa.curriculum.concept_net import concept_of, meaning_graph
    from casa.curriculum.parse import _name_index, resolve_token
    from casa.curriculum.roundtrip import realize_graph

    names = _name_index(state, lattice_id)
    targets = [c for t in toks if t not in ("из", "чего", "что")
               and (c := (concept_of(state, lattice_id, t) or resolve_token(state, lattice_id, t, names)))]
    if not targets:
        return None
    target = targets[-1]
    edges = _scan_memory_full(state, lattice_id, _edge_re("made_of", target, None))
    if edges:
        g = meaning_graph(state, lattice_id, [edges[0]])
        answer = realize_graph(state, lattice_id, g, lang="ru")
        if answer:
            return answer
    return f"Пока не знаю, из чего «{_ru_name(state, lattice_id, target)}» — мне про это не говорили."


def answer_question(state: dict, lattice_id: str, text: str) -> str | None:
    """Answer a question via the conceptual network, or None if it is not a known form."""
    toks = _tokens(text)
    if not toks:
        return None
    return (
        _answer_comparison(state, lattice_id, toks)
        or _answer_color(state, lattice_id, toks)
        or _answer_material(state, lattice_id, toks)
        or _answer_affordance(state, lattice_id, toks)
        or _answer_location(state, lattice_id, toks)
    )
