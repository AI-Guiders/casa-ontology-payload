#!/usr/bin/env python3
"""Clause constructions — tense, negation, and questions over the S-V-O core.

English do-support: under negation and yes/no questions an auxiliary (does/did)
carries tense and agreement while the main verb stays in its base form; the plain
declarative inflects the main verb itself. Three constructions are stored on the
field as ordered slot templates and applied by reading them back, so ablating a
template collapses that construction (the gate's honesty rests on this):

    decl  [subj, vfin,  obj]            The cat drinks the water.   / drank (past)
    neg   [subj, aux, neg, vbase, obj]  The cat does not drink the water. / did not
    quest [aux, subj, vbase, obj]       Does the cat drink the water?    / Did ...

Forms come from the morphology rules already learned: present agreement from the 3sg
rule, past from the past rule. Irregular pasts (drink->drank) are a small GIVEN
lexicon — they are suppletive, not derivable from spelling. Same ceiling as before:
generation from given roles+features, not parsing; article fixed to a determiner.
"""

from __future__ import annotations

from typing import Any

from casa.curriculum.compose import (
    apply_conditioned_rule,
    compose_np,
    read_order_rule,
    teach_np_order,
    teach_order_rule,
)
from casa.curriculum.translate import translate_term

PRESENT3SG = "lang.rule.present3sg.en"
PAST = "lang.rule.past.en"

CONSTRUCTIONS: dict[str, list[str]] = {
    "decl": ["subj", "vfin", "obj"],
    "neg": ["subj", "aux", "neg", "vbase", "obj"],
    "quest": ["aux", "subj", "vbase", "obj"],
}
_AUX = {"present": "does", "past": "did"}  # suppletive auxiliary forms (given)


def _rule_id(construction: str) -> str:
    return f"lang.clause.{construction}.en"


def teach_clause_constructions(state: dict, lattice_id: str) -> dict[str, Any]:
    """Store the three clause templates on the field."""
    for name, order in CONSTRUCTIONS.items():
        teach_order_rule(state, lattice_id, _rule_id(name), order)
    return {"stored": list(CONSTRUCTIONS)}


def _construction_for(polarity: str, mood: str) -> str:
    if mood == "interrogative":
        return "quest"
    return "neg" if polarity == "negative" else "decl"


def compose_clause(
    state: dict,
    lattice_id: str,
    *,
    subj: str,
    verb: str,
    obj: str,
    tense: str = "present",
    polarity: str = "affirmative",
    mood: str = "declarative",
    lang_in: str = "ru",
    determiner: str = "the",
    irregular_past: dict[str, str] | None = None,
    punctuate: bool = True,
) -> str | None:
    """Compose an English clause for the given meaning triple and grammatical features
    (None if a word is unknown or the construction template is absent)."""
    irregular_past = irregular_past or {}

    def en(word: str) -> str | None:
        if lang_in == "en":
            return word
        hits = translate_term(state, lattice_id, word, to_script="latn")
        return hits[0] if hits else None

    s_en, v_en, o_en = en(subj), en(verb), en(obj)
    if not (s_en and v_en and o_en):
        return None

    if tense == "past":
        vfin = irregular_past.get(v_en) or apply_conditioned_rule(state, lattice_id, PAST, v_en) or v_en
    else:
        vfin = apply_conditioned_rule(state, lattice_id, PRESENT3SG, v_en) or v_en

    fillers = {
        "subj": f"{determiner} {s_en}".strip(),
        "obj": f"{determiner} {o_en}".strip(),
        "vfin": vfin,
        "vbase": v_en,
        "aux": _AUX.get(tense, "does"),
        "neg": "not",
    }
    construction = _construction_for(polarity, mood)
    order = read_order_rule(state, lattice_id, _rule_id(construction))
    if not order or any(slot not in fillers for slot in order):
        return None
    sentence = " ".join(fillers[slot] for slot in order)
    if punctuate:
        end = "?" if mood == "interrogative" else "."
        sentence = sentence[:1].upper() + sentence[1:] + end
    return sentence


def compose_full_clause(
    state: dict,
    lattice_id: str,
    *,
    subject: dict[str, Any],
    obj: dict[str, Any],
    verb: str,
    tense: str = "present",
    polarity: str = "affirmative",
    mood: str = "declarative",
    lang_in: str = "ru",
    determiner: str = "the",
    irregular_past: dict[str, str] | None = None,
    punctuate: bool = True,
) -> str | None:
    """Compose a clause whose subject/object are full noun phrases (determiner, number,
    adjective, plural). The SUBJECT's number drives verb agreement: a plural subject
    takes the base verb and the ``do`` auxiliary, a singular subject the 3sg verb and
    ``does``; past is ``did`` and does not agree in number.

    ``subject``/``obj`` are NP specs: ``{noun, adj?, number?, determiner?, plural?}``.
    """
    irregular_past = irregular_past or {}
    s_text, s_plural = compose_np(state, lattice_id, lang_in=lang_in, **{"determiner": determiner, **subject})
    o_text, _ = compose_np(state, lattice_id, lang_in=lang_in, **{"determiner": determiner, **obj})
    if not s_text or not o_text:
        return None

    def en(word: str) -> str | None:
        if lang_in == "en":
            return word
        hits = translate_term(state, lattice_id, word, to_script="latn")
        return hits[0] if hits else None

    v_en = en(verb)
    if not v_en:
        return None

    if tense == "past":
        vfin = irregular_past.get(v_en) or apply_conditioned_rule(state, lattice_id, PAST, v_en) or v_en
        aux = "did"
    elif s_plural:
        vfin, aux = v_en, "do"  # plural subject: base verb, "do"
    else:
        vfin = apply_conditioned_rule(state, lattice_id, PRESENT3SG, v_en) or v_en
        aux = "does"

    fillers = {"subj": s_text, "obj": o_text, "vfin": vfin, "vbase": v_en, "aux": aux, "neg": "not"}
    construction = _construction_for(polarity, mood)
    order = read_order_rule(state, lattice_id, _rule_id(construction))
    if not order or any(slot not in fillers for slot in order):
        return None
    sentence = " ".join(fillers[slot] for slot in order)
    if punctuate:
        sentence = sentence[:1].upper() + sentence[1:] + ("?" if mood == "interrogative" else ".")
    return sentence


def gate_clause_constructions(
    state: dict,
    lattice_id: str,
    cases: list[tuple[dict[str, str], str]],
    *,
    pass_ratio: float = 0.9,
) -> dict[str, Any]:
    """Verify the constructions generate HELD-OUT (features x triple) cases correctly.

    Controls: ablation drops every construction template (production must collapse),
    and a negative control swaps the question and declarative orders (the affected
    cases must no longer match). Requires the glossary + morphology rules taught.
    """
    from casa.prisms.memory.f0_stack import weaken_graph_edge
    from casa.prisms.memory.memory_prisms import memory_lattices

    teach_clause_constructions(state, lattice_id)

    def compose(feat: dict[str, str]) -> str | None:
        return compose_clause(state, lattice_id, **feat)

    passes = [compose(f) == expected for f, expected in cases]
    held_rate = sum(passes) / len(passes) if passes else 0.0

    # ablation: drop all construction templates -> production collapses
    for name, order in CONSTRUCTIONS.items():
        for i, slot in enumerate(order):
            weaken_graph_edge(memory_lattices(state), lattice_id, _rule_id(name), "order", f"lang.slot.{slot}@{i}")
    ablation_breaks = all(compose(f) is None for f, _ in cases)

    # negative control: swap declarative <-> question order; their cases must not match
    teach_order_rule(state, lattice_id, _rule_id("decl"), CONSTRUCTIONS["quest"])
    teach_order_rule(state, lattice_id, _rule_id("quest"), CONSTRUCTIONS["decl"])
    affected = [(f, e) for f, e in cases if f.get("mood") == "interrogative" or f.get("polarity", "affirmative") != "negative"]
    negative_control_passed = not any(compose(f) == e for f, e in affected)
    teach_clause_constructions(state, lattice_id)  # restore

    passed = bool(
        len(cases) >= 3
        and held_rate >= pass_ratio
        and ablation_breaks
        and negative_control_passed
    )
    return {
        "passed": passed,
        "cases": len(cases),
        "held_out_pass_rate": round(held_rate, 3),
        "negative_control_passed": negative_control_passed,
        "ablation_breaks_production": ablation_breaks,
    }


def gate_full_clause(
    state: dict,
    lattice_id: str,
    cases: list[tuple[dict[str, Any], str]],
    *,
    pass_ratio: float = 0.9,
) -> dict[str, Any]:
    """Verify the integrated NP+clause generator on HELD-OUT (features x specs) cases.

    Controls: ablation drops the NP order edges (production must collapse), and a
    negative control reverses the NP order (cases with an adjective/number must no
    longer match). Requires the glossary + morphology rules + clause templates taught.
    """
    from casa.prisms.memory.f0_stack import weaken_graph_edge
    from casa.prisms.memory.memory_prisms import memory_lattices

    from casa.curriculum.compose import NP_RULE, _NP_ORDER

    teach_np_order(state, lattice_id)

    def compose(feat: dict[str, Any]) -> str | None:
        return compose_full_clause(state, lattice_id, **feat)

    passes = [compose(f) == expected for f, expected in cases]
    held_rate = sum(passes) / len(passes) if passes else 0.0

    # ablation: drop the NP order edges -> noun phrases (so clauses) collapse
    for i, slot in enumerate(_NP_ORDER):
        weaken_graph_edge(memory_lattices(state), lattice_id, NP_RULE, "order", f"lang.slot.{slot}@{i}")
    ablation_breaks = all(compose(f) is None for f, _ in cases)

    # negative control: reverse NP order; cases with adj/number must no longer match
    teach_order_rule(state, lattice_id, NP_RULE, list(reversed(_NP_ORDER)))
    affected = [(f, e) for f, e in cases if f.get("subject", {}).get("adj") or f.get("subject", {}).get("number")]
    negative_control_passed = not any(compose(f) == e for f, e in affected) if affected else True
    teach_np_order(state, lattice_id)  # restore

    passed = bool(
        len(cases) >= 3
        and held_rate >= pass_ratio
        and ablation_breaks
        and negative_control_passed
    )
    return {
        "passed": passed,
        "cases": len(cases),
        "held_out_pass_rate": round(held_rate, 3),
        "negative_control_passed": negative_control_passed,
        "ablation_breaks_production": ablation_breaks,
    }
