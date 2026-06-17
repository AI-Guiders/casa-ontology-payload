#!/usr/bin/env python3
"""Grounded generation — validate a meaning triple against the conceptual network
BEFORE rendering it, so the generator refuses nonsense instead of producing it.

The verb is mapped to a conceptual-network relation (читать/read -> read, есть/eat -> eat,
…); the subject and object must satisfy that relation's selectional constraints
(read needs an agent reading something readable). A triple that violates them is
REFUSED with a reason; a valid triple is rendered in both languages. Verbs with no
known constraint are unconstrained (generated, not blocked) — the system only refuses
when it KNOWS the combination is wrong.

  студент + читать + книга  -> "The student reads the book." / «Студент читает книгу.»
  стол    + читать + книга  -> refused: table is not an agent (cannot read)
  человек + есть   + камень -> refused: stone is not edible
"""

from __future__ import annotations

from typing import Any

from casa.curriculum.bilingual import bilingual_clause
from casa.curriculum.concept_net import validate

# verb lemma (RU or EN) -> conceptual-network relation
VERB_RELATION: dict[str, str] = {
    "читать": "read", "read": "read",
    "есть": "eat", "eat": "eat",
    "пить": "drink", "drink": "drink",
    "wear": "wear",
    "ride": "ride", "ездить": "ride",
    "use": "use", "использовать": "use",
}


def meaningful(state: dict, lattice_id: str, subj: str, verb: str, obj: str) -> dict[str, Any]:
    """Is ``verb(subj, obj)`` sensible? Validates via the conceptual network when the
    verb maps to a known relation; otherwise reports ``unconstrained`` (allowed)."""
    rel = VERB_RELATION.get(verb.strip().lower())
    if rel is None:
        return {"valid": True, "relation": None, "reason": "unconstrained"}
    v = validate(state, lattice_id, rel, subj, obj)
    return {
        "valid": bool(v["valid"]),
        "relation": rel,
        "reason": v.get("reason"),
        "arg1_ok": v.get("arg1_ok"),
        "arg2_ok": v.get("arg2_ok"),
        "needs": v.get("needs"),
    }


def guarded_clause(
    state: dict,
    lattice_id: str,
    *,
    subj: str,
    verb: str,
    obj: str,
    source: str = "ru",
    **features: Any,
) -> dict[str, Any]:
    """Validate the triple, then render it bilingually — or refuse with a reason.

    Returns ``{valid, relation, reason, ru, en}``; on refusal ``ru``/``en`` are None."""
    m = meaningful(state, lattice_id, subj, verb, obj)
    if not m["valid"]:
        return {"valid": False, "relation": m["relation"], "reason": m["reason"], "ru": None, "en": None}
    out = bilingual_clause(state, lattice_id, subj=subj, verb=verb, obj=obj, source=source, **features)
    return {"valid": True, "relation": m["relation"], "reason": "ok", **out}


def gate_grounded(
    state: dict,
    lattice_id: str,
    sensible: list[tuple[str, str, str]],
    nonsense: list[tuple[str, str, str]],
    *,
    source: str = "ru",
) -> dict[str, Any]:
    """Sensible triples must render (both sides non-None); nonsense triples must be
    refused (valid False, no surface). Ontology + grammars must be taught already."""
    rendered = [guarded_clause(state, lattice_id, subj=s, verb=v, obj=o, source=source) for s, v, o in sensible]
    refused = [guarded_clause(state, lattice_id, subj=s, verb=v, obj=o, source=source) for s, v, o in nonsense]
    sense_ok = sum(bool(r["valid"] and r.get("en")) for r in rendered)
    nonsense_ok = sum(bool((not r["valid"]) and r["en"] is None) for r in refused)
    sense_rate = sense_ok / len(sensible) if sensible else 0.0
    passed = bool(
        len(sensible) >= 3
        and len(nonsense) >= 3
        and sense_rate >= 0.9
        and nonsense_ok == len(nonsense)
    )
    return {
        "passed": passed,
        "sensible": len(sensible),
        "nonsense": len(nonsense),
        "sensible_render_rate": round(sense_rate, 3),
        "all_nonsense_refused": nonsense_ok == len(nonsense),
    }
