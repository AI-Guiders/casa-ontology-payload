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

# lab-only ephemeral lattice (ADR-0083 §5): build_meaning_state is the round-trip/validator
# harness, NOT the agent store. The normative Built-In Concept Zone is taught onto
# `agent-concept-graph` @ prism_agent (concept_built_in.py / teach_curriculum_ontology.py);
# this `schema-math` lattice here is lab scaffolding and not the store model.
LATTICE = "schema-math"
_RU_RULES = (
    "lang.rule.acc-sg.ru", "lang.rule.present3sg.ru", "lang.rule.prep-sg.ru",
    "lang.rule.gen-sg-m.ru", "lang.rule.gen-sg-n.ru", "lang.rule.gen-sg-f.ru",
)


def _teach_colors(state: dict) -> None:
    """Colours as concepts + the ``color_of`` relation, so «яблоко красное» validates and
    «какого цвета яблоко?» can be answered. The colour concept ids mirror the adjective
    attribute ids (red → concept.red); names come from the adjective lexicon, not a glossary."""
    from casa.curriculum.attributes import COLOR_IDS
    from casa.curriculum.concept_net import teach_affords, teach_isa, teach_relation

    teach_isa(state, LATTICE, [(f"concept.{c}", "colour_concept") for c in COLOR_IDS])
    teach_affords(state, LATTICE, [("colour_concept", "is_colour"),
                                   ("physical_object", "colorable"), ("digital_object", "colorable")])
    teach_relation(state, LATTICE, "color_of", arg1="colorable", arg2="is_colour")
    # comparison: «слон больше мыши» — both must be sizable (physical things have a size)
    teach_affords(state, LATTICE, [("physical_object", "sizable")])
    teach_relation(state, LATTICE, "bigger_than", arg1="sizable", arg2="sizable")


def _teach_states(state: dict) -> None:
    """Predicative states as concepts + the ``has_state`` relation, so «файл открыт» /
    «the file is open» validates and feeds conditional rules. State concept ids mirror the
    state ids (open → concept.open); a thing must be ``stateful`` to carry a state (an idea
    is not). Multiple states are allowed (open AND saved); only polarity contradicts."""
    from casa.curriculum.concept_net import teach_affords, teach_isa, teach_relation
    from casa.curriculum.states import STATE_IDS

    teach_isa(state, LATTICE, [(f"concept.{s}", "a_state") for s in STATE_IDS])
    teach_affords(state, LATTICE, [("a_state", "is_state"),
                                   ("digital_object", "stateful"), ("physical_object", "stateful")])
    teach_relation(state, LATTICE, "has_state", arg1="stateful", arg2="is_state")


def _teach_amounts(state: dict) -> None:
    """Numeric thresholds as concepts + comparison relations, so «доза больше 5 мл» /
    «files more than two» validates and feeds value-mutex reasoning (gt/lt/eq over the same
    quantity that are mutually exclusive: «больше 10» vs «меньше 5»). The threshold's
    value+unit ride as a measure on the single ``concept.amount`` node; the operator is the
    relation (num_gt/num_lt/num_eq)."""
    from casa.curriculum.concept_net import teach_affords, teach_isa, teach_relation

    teach_isa(state, LATTICE, [("concept.amount", "amount")])
    teach_affords(state, LATTICE, [("amount", "is_amount"),
                                   ("physical_object", "measurable"), ("digital_object", "measurable"),
                                   ("substance", "measurable"), ("abstraction", "measurable")])
    for rel in ("num_gt", "num_lt", "num_eq"):
        teach_relation(state, LATTICE, rel, arg1="measurable", arg2="is_amount")


# Spanish surfaces for concepts ALREADY in the ontology (general layer + software pack) —
# the benchmark/demo scope, not a full lexicon. Concept id -> Spanish names (incl. gendered
# noun variants where common). Plurals resolve via the -s/-es lemma strip in resolve_token.
_ES_NAMES: dict[str, list[str]] = {
    # everyday
    "concept.water": ["agua"], "concept.table": ["mesa"], "concept.apple": ["manzana"],
    "concept.book": ["libro"], "concept.milk": ["leche"], "concept.meat": ["carne"],
    "concept.bread": ["pan"], "concept.house": ["casa"], "concept.dog": ["perro", "perra"],
    "concept.cat": ["gato", "gata"], "concept.chair": ["silla"], "concept.wood": ["madera"],
    "concept.glass": ["vidrio"], "concept.iron": ["hierro"], "concept.box": ["caja"],
    "concept.cup": ["taza"], "concept.door": ["puerta"], "concept.window": ["ventana"],
    "concept.person": ["persona"], "concept.man": ["hombre"], "concept.woman": ["mujer"],
    "concept.child": ["niño", "niña"], "concept.elephant": ["elefante"],
    "concept.mouse": ["ratón", "raton"], "concept.bird": ["pájaro", "pajaro"],
    "concept.fish": ["pez"], "concept.horse": ["caballo"], "concept.cow": ["vaca"],
    "concept.juice": ["jugo", "zumo"], "concept.tea": ["té"], "concept.coffee": ["café"],
    # software/UI pack
    "concept.file": ["archivo", "fichero"], "concept.document": ["documento"],
    "concept.folder": ["carpeta"], "concept.directory": ["directorio"],
    "concept.button": ["botón", "boton"], "concept.icon": ["icono"], "concept.menu": ["menú"],
    "concept.tab": ["pestaña"], "concept.link": ["enlace"], "concept.checkbox": ["casilla"],
    "concept.toolbar": ["panel"], "concept.list": ["lista"], "concept.item": ["elemento"],
    "concept.editor": ["editor"],
    "concept.application": ["aplicación", "aplicacion"], "concept.program": ["programa"],
    "concept.clipboard": ["portapapeles"], "concept.disk": ["disco"],
    "concept.trash": ["papelera"], "concept.setting": ["ajuste", "configuración"],
    "concept.option": ["opción", "opcion"], "concept.parameter": ["parámetro", "parametro"],
    "concept.user": ["usuario", "usuaria"], "concept.image": ["imagen"],
}


def _teach_es_names(state: dict) -> None:
    """Spanish vocabulary layer: name edges for existing concepts (parse-side only — the
    Spanish realizer is out of scope; the validator needs parsing, not generation)."""
    from casa.curriculum.concept_net import teach_names

    teach_names(state, LATTICE, [(cid, s) for cid, surfaces in _ES_NAMES.items() for s in surfaces],
                lang="es")


def _teach_verbs(state: dict) -> None:
    """Everyday transitive verbs whose constraints aren't in the base ontology yet
    (wear/use/read/eat/drink already are). Each: an arg2 affordance + the relation."""
    from casa.curriculum.concept_net import teach_affords, teach_relation

    teach_affords(state, LATTICE, [
        ("document", "writable"), ("food", "cookable"),
        ("physical_object", "washable"),  # washing is broadly applicable (an idea is not washable)
        ("place", "habitat"),  # animals live in places («кошка живёт в доме»)
    ])
    for rel, arg2 in [("write", "writable"), ("cook", "cookable"), ("wash", "washable"),
                      ("give", "ownable"), ("take", "ownable")]:  # ownable: any physical_object
        teach_relation(state, LATTICE, rel, arg1="agent", arg2=arg2)
    teach_relation(state, LATTICE, "lives_in", arg1="agent", arg2="habitat")


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
    _teach_colors(state)  # color_of relation + colour concepts
    _teach_states(state)  # has_state relation + predicative state concepts (open/active/…)
    _teach_amounts(state)  # num_gt/num_lt/num_eq comparison relations + amount concept
    _teach_verbs(state)  # everyday transitive verbs (write/cook/wash/give/take)
    _teach_es_names(state)  # Spanish vocabulary layer (parse-side, benchmark scope)
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
