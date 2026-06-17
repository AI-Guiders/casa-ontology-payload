#!/usr/bin/env python3
"""Sentence-level generation — build a simple English clause from a meaning triple.

This stacks everything below it: the glossary (RU->EN words), morphology (subject-verb
agreement via the 3sg rule), and a constituent-order rule INDUCED from example
sentences and stored on the field. Given a role-tagged triple
(subject, verb, object) it produces an ordered, agreeing English clause:

    {subj: кот, verb: пить, obj: вода}  ->  "the cat drinks the water"

Honest ceiling: this is generation FROM structured meaning (the roles are given), not
parsing free Russian text into roles — role assignment is understanding, which the
substrate does not do. Article selection is simplified to a fixed determiner (English
a/the/none is genuinely hard). Order is learned and field-stored, so ablating it
breaks production, which is what makes the gate honest.
"""

from __future__ import annotations

from typing import Any

from casa.curriculum.compose import apply_conditioned_rule, read_order_rule, teach_order_rule
from casa.curriculum.translate import translate_term

SVO_RULE = "lang.sentence.svo.en"
AGREE_RULE = "lang.rule.present3sg.en"

RU_SVO_RULE = "lang.sentence.svo.ru"
RU_CONJ_RULE = "lang.rule.present3sg.ru"
RU_ACC_RULE = "lang.rule.acc-sg.ru"


def induce_order_from_examples(examples: list[tuple[dict[str, str], list[str]]]) -> list[str] | None:
    """Learn constituent order from ``(roles, surface_words)`` examples.

    Each role's filler is located in the surface word list; the order is the roles
    sorted by position. Returns None if the examples disagree or a filler is missing —
    the learner declines rather than guess an inconsistent order.
    """
    order: list[str] | None = None
    for roles, surface in examples:
        try:
            positions = {role: surface.index(word) for role, word in roles.items()}
        except ValueError:
            return None
        this = [role for role, _ in sorted(positions.items(), key=lambda kv: kv[1])]
        if order is None:
            order = this
        elif order != this:
            return None
    return order


def teach_sentence_order(
    state: dict, lattice_id: str, examples: list[tuple[dict[str, str], list[str]]], *, rule_id: str = SVO_RULE
) -> dict[str, Any]:
    """Induce the constituent order from examples and store it on the field."""
    order = induce_order_from_examples(examples)
    if order is None:
        return {"rule_id": rule_id, "order": None, "stored": False}
    teach_order_rule(state, lattice_id, rule_id, order)
    return {"rule_id": rule_id, "order": order, "stored": True}


def compose_sentence(
    state: dict,
    lattice_id: str,
    *,
    subj: str,
    verb: str,
    obj: str,
    lang_in: str = "ru",
    determiner: str = "the",
    rule_id: str = SVO_RULE,
    agree_rule: str = AGREE_RULE,
    punctuate: bool = True,
) -> str | None:
    """Compose an English S-V-O clause from a meaning triple (None if a word is unknown
    or the order rule is absent)."""
    def en(word: str) -> str | None:
        if lang_in == "en":
            return word
        hits = translate_term(state, lattice_id, word, to_script="latn")
        return hits[0] if hits else None

    s_en, v_en, o_en = en(subj), en(verb), en(obj)
    if not (s_en and v_en and o_en):
        return None

    # subject is 3rd person singular -> agree the verb (falls back to the lemma)
    v_agreed = apply_conditioned_rule(state, lattice_id, agree_rule, v_en) or v_en

    fillers = {
        "subj": f"{determiner} {s_en}".strip(),
        "verb": v_agreed,
        "obj": f"{determiner} {o_en}".strip(),
    }
    order = read_order_rule(state, lattice_id, rule_id)
    if not order or any(slot not in fillers for slot in order):
        return None
    words = [fillers[slot] for slot in order]
    sentence = " ".join(words)
    if punctuate:
        sentence = sentence[:1].upper() + sentence[1:] + "."
    return sentence


def compose_ru_clause(
    state: dict,
    lattice_id: str,
    *,
    subj: str,
    verb: str,
    obj: str,
    conj_rule: str = RU_CONJ_RULE,
    acc_rule: str = RU_ACC_RULE,
    rule_id: str = RU_SVO_RULE,
    punctuate: bool = True,
) -> str | None:
    """Compose a Russian S-V-O clause from a meaning triple (all words already Russian).

    The subject stays nominative (its base form), the verb is conjugated to 3rd person
    singular by the learned rule, and the object is declined to the accusative — so
    «девочка читать книга» -> «Девочка читает книгу.» No articles. Returns None if the
    order rule is absent. Verbs/nouns whose forms the rules don't cover fall back to the
    lemma (honest: irregular conjugation / soft stems are out of scope)."""
    v = apply_conditioned_rule(state, lattice_id, conj_rule, verb) or verb
    o = apply_conditioned_rule(state, lattice_id, acc_rule, obj) or obj
    fillers = {"subj": subj, "verb": v, "obj": o}
    order = read_order_rule(state, lattice_id, rule_id)
    if not order or any(slot not in fillers for slot in order):
        return None
    sentence = " ".join(fillers[slot] for slot in order)
    if punctuate:
        sentence = sentence[:1].upper() + sentence[1:] + "."
    return sentence


def gate_ru_clause(
    state: dict,
    lattice_id: str,
    examples: list[tuple[dict[str, str], list[str]]],
    held_out: list[tuple[dict[str, str], str]],
    *,
    rule_id: str = RU_SVO_RULE,
    pass_ratio: float = 0.9,
) -> dict[str, Any]:
    """Induce RU S-V-O order from examples, verify held-out triples (conjugation +
    accusative), with negative control (reversed order) and ablation. The conjugation
    and accusative rules must be taught into ``state`` already."""
    from casa.prisms.memory.f0_stack import weaken_graph_edge
    from casa.prisms.memory.memory_prisms import memory_lattices

    rep = teach_sentence_order(state, lattice_id, examples, rule_id=rule_id)
    if not rep["stored"]:
        return {"passed": False, "reason": "no_order_induced", "rule_id": rule_id}
    order = rep["order"]

    def compose(triple: dict[str, str]) -> str | None:
        return compose_ru_clause(state, lattice_id, rule_id=rule_id, **triple)

    passes = [compose(t) == expected for t, expected in held_out]
    held_rate = sum(passes) / len(passes) if passes else 0.0

    for i, slot in enumerate(order):
        weaken_graph_edge(memory_lattices(state), lattice_id, rule_id, "order", f"lang.slot.{slot}@{i}")
    ablation_breaks = all(compose(t) is None for t, _ in held_out)

    teach_order_rule(state, lattice_id, rule_id, list(reversed(order)))
    negative_control_passed = not any(compose(t) == expected for t, expected in held_out)
    teach_order_rule(state, lattice_id, rule_id, order)

    passed = bool(
        len(held_out) >= 3 and held_rate >= pass_ratio and ablation_breaks and negative_control_passed
    )
    return {
        "passed": passed,
        "rule_id": rule_id,
        "order": order,
        "held_out": len(held_out),
        "held_out_pass_rate": round(held_rate, 3),
        "negative_control_passed": negative_control_passed,
        "ablation_breaks_production": ablation_breaks,
    }


def gate_sentence_order(
    state: dict,
    lattice_id: str,
    examples: list[tuple[dict[str, str], list[str]]],
    held_out: list[tuple[dict[str, str], str]],
    *,
    rule_id: str = SVO_RULE,
    pass_ratio: float = 0.9,
    determiner: str = "the",
) -> dict[str, Any]:
    """Induce order from examples, then verify it generates HELD-OUT triples correctly.

    Controls: a negative control trains the REVERSED order (held-out must then NOT
    match), and ablation removes the order edges (production must collapse). Requires
    the glossary + agreement rule to be taught into ``state`` already.
    """
    from casa.prisms.memory.f0_stack import weaken_graph_edge
    from casa.prisms.memory.memory_prisms import memory_lattices

    rep = teach_sentence_order(state, lattice_id, examples, rule_id=rule_id)
    if not rep["stored"]:
        return {"passed": False, "reason": "no_order_induced", "rule_id": rule_id}
    order = rep["order"]

    def compose(triple: dict[str, str]) -> str | None:
        return compose_sentence(state, lattice_id, rule_id=rule_id, determiner=determiner, **triple)

    passes = [compose(t) == expected for t, expected in held_out]
    held_rate = sum(passes) / len(passes) if passes else 0.0

    # ablation: drop the order edges, production must collapse
    for i, slot in enumerate(order):
        weaken_graph_edge(memory_lattices(state), lattice_id, rule_id, "order", f"lang.slot.{slot}@{i}")
    ablation_breaks = all(compose(t) is None for t, _ in held_out)

    # negative control: store the reversed order — held-out must no longer match
    teach_order_rule(state, lattice_id, rule_id, list(reversed(order)))
    negative_control_passed = not any(compose(t) == expected for t, expected in held_out)
    # restore the learned order
    teach_order_rule(state, lattice_id, rule_id, order)

    passed = bool(
        len(held_out) >= 3
        and held_rate >= pass_ratio
        and ablation_breaks
        and negative_control_passed
    )
    return {
        "passed": passed,
        "rule_id": rule_id,
        "order": order,
        "held_out": len(held_out),
        "held_out_pass_rate": round(held_rate, 3),
        "negative_control_passed": negative_control_passed,
        "ablation_breaks_production": ablation_breaks,
    }
