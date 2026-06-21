#!/usr/bin/env python3
"""Build a ready-to-use conceptual-network state (ontology + the rules round-trip needs).

One call returns a field state with the base ontology, the Russian/English morphology
rules, the clause grammars, and the orders the meaning round-trip relies on — so the
conceptual network can be used from anywhere (e.g. a `/meaning` command in the chat)
without re-wiring the teaching each time. Self-contained; touches nothing global.
"""

from __future__ import annotations

import json

from casa._paths import REPO_ROOT

LATTICE = "schema-math"
_RU_RULES = (
    "lang.rule.acc-sg.ru", "lang.rule.present3sg.ru", "lang.rule.prep-sg.ru",
    "lang.rule.gen-sg-m.ru", "lang.rule.gen-sg-n.ru", "lang.rule.gen-sg-f.ru",
)


def build_meaning_state() -> tuple[dict, str]:
    """Return ``(state, lattice_id)`` with the conceptual network + round-trip grammars taught."""
    from casa.curriculum.clause import teach_clause_constructions
    from casa.curriculum.compose import teach_conditioned_rule, teach_np_order
    from casa.curriculum.concept_net import teach_concept_net
    from casa.curriculum.sentence import RU_SVO_RULE, teach_sentence_order
    from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
    from casa.prisms.memory.memory_prisms import ensure_prisms

    def _load(rel: str) -> dict:
        return json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))

    bundle = _load("lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json")
    state = ensure_prisms({})
    ingest_math_bundle(state, bundle)
    wide = REPO_ROOT / "lab/curriculum/concept-net-wide-v1.json"  # prefer the wide ontology
    net = "lab/curriculum/concept-net-wide-v1.json" if wide.exists() else "lab/curriculum/concept-net-base-v1.json"
    teach_concept_net(state, LATTICE, _load(net), bundle=bundle)
    from casa.curriculum.software_domain import teach_software_domain

    teach_software_domain(state, LATTICE, bundle=bundle)  # additive software/UI layer
    ru = _load("lab/curriculum/ru-rules-v1.json")["rules"]
    en = _load("lab/curriculum/en-rules-v1.json")["rules"]
    for rid in _RU_RULES:
        teach_conditioned_rule(state, LATTICE, rid, [tuple(p) for p in ru[rid]])
    teach_conditioned_rule(state, LATTICE, "lang.rule.present3sg.en", [tuple(p) for p in en["lang.rule.present3sg.en"]])
    teach_clause_constructions(state, LATTICE)
    teach_np_order(state, LATTICE)
    teach_sentence_order(
        state, LATTICE,
        [({"subj": "кот", "verb": "читает", "obj": "книгу"}, ["кот", "читает", "книгу"])],
        rule_id=RU_SVO_RULE,
    )
    return state, LATTICE
