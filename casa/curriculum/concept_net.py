#!/usr/bin/env python3
"""Conceptual network — affordance/type grounding and validation (Dmitry's «понятийная сеть»).

Objects carry a small set of types/affordances and relations carry selectional
constraints; a combination is VALIDATED deterministically against them. The map lives
on CONCEPTS, and the glossary's ``concept|names|word`` edges bridge to any language —
so «яблоко на столе» and "apple on the table" validate to the same relation, in the
same way, with no statistical model and no hallucination.

  isa     taxonomy with inheritance:  lex.apple|isa|fruit, fruit|isa|food, fruit|isa|physical_object
  affords capabilities on a type:     food|affords|edible, physical_object|affords|positionable
  arg1/2  a relation's selectional constraints: on|arg1|positionable, on|arg2|support_surface

A concept's affordances = the union of ``affords`` over its isa-closure, so a never-seen
object inherits them (banana isa fruit isa food -> edible). validate() checks the
relation's argument roles against the two concepts' affordances.

Honest ceiling: this checks type/affordance compatibility (catches category errors like
«идея на столе»); it is not full physics or pragmatics, and the ontology is curated
(authored), not induced from raw text. Scope it to a domain.
"""

from __future__ import annotations

from typing import Any

from casa.curriculum.translate import concepts_for_term

_ISA = "isa"
_AFFORDS = "affords"
_HAS_PART = "has_part"


def _lattices(state: dict) -> dict:
    from casa.prisms.memory.memory_prisms import memory_lattices

    return memory_lattices(state)


def _edges(state: dict, lattice_id: str) -> list[str]:
    from casa.prisms.memory.f0_stack import decode_f0_lattice

    lat = _lattices(state).get(lattice_id)
    return list(decode_f0_lattice(lat).get("edges") or []) if lat else []


def _mint(state: dict, lattice_id: str, src: str, rel: str, dst: str, *, copies: int = 4) -> None:
    from casa.prisms.memory.f0_stack import strengthen_graph_edge

    strengthen_graph_edge(_lattices(state), lattice_id, src, rel, dst, copies=copies)


# --------------------------------------------------------------------------- #
# teach the ontology (all field-stored, ablatable)
# --------------------------------------------------------------------------- #
def teach_isa(state: dict, lattice_id: str, pairs: list[tuple[str, str]]) -> None:
    """Mint taxonomy edges ``sub|isa|super``."""
    for sub, sup in pairs:
        _mint(state, lattice_id, sub, _ISA, sup)


def teach_affords(state: dict, lattice_id: str, pairs: list[tuple[str, str]]) -> None:
    """Mint capability edges ``type|affords|role``."""
    for typ, role in pairs:
        _mint(state, lattice_id, typ, _AFFORDS, role)


def teach_relation(state: dict, lattice_id: str, rel: str, *, arg1: str, arg2: str) -> None:
    """Mint a relation's selectional constraints ``rel|arg1|role`` / ``rel|arg2|role``."""
    _mint(state, lattice_id, rel, "arg1", arg1)
    _mint(state, lattice_id, rel, "arg2", arg2)


def teach_parts(state: dict, lattice_id: str, pairs: list[tuple[str, str]]) -> None:
    """Mint mereology edges ``whole|has_part|part``. ``whole`` may be a category (so all
    its members inherit the part) or a concept id; ``part`` is a concept id."""
    for whole, part in pairs:
        _mint(state, lattice_id, whole, _HAS_PART, part)


def parts_of(state: dict, lattice_id: str, whole: str) -> set[str]:
    """All parts of ``whole`` (asserted on it or on any of its super-types)."""
    edges = _edges(state, lattice_id)
    out: set[str] = set()
    for typ in isa_closure(state, lattice_id, whole):
        p = f"{typ}|{_HAS_PART}|"
        out |= {e[len(p):] for e in edges if e.startswith(p)}
    return out


def has_part(state: dict, lattice_id: str, whole: str, part: str) -> bool:
    """Does ``whole`` have ``part`` (asserted, inherited along isa)? Cross-lingual."""
    cw, cp = concept_of(state, lattice_id, whole), concept_of(state, lattice_id, part)
    if cw is None or cp is None:
        return False
    return cp in parts_of(state, lattice_id, cw)


def _concept_id(en: str) -> str:
    return f"lex.{en.strip().lower().replace(' ', '_')}"


def teach_concept_net(state: dict, lattice_id: str, data: dict, *, bundle: dict | None = None) -> dict[str, Any]:
    """Load a whole ontology bundle: cross-lingual names (glossary), category taxonomy,
    leaf isa, type affordances, and relation constraints. Returns counts.

    ``data`` shape: ``{categories:[{id,isa,affords}], concepts:{category:[[ru,en],...]},
    relations:[{rel,arg1,arg2}]}``."""
    from casa.curriculum.glossary import teach_glossary

    pairs = [(ru, en) for cat in data["concepts"].values() for ru, en in cat]
    teach_glossary(state, pairs, lattice_id=lattice_id, bundle=bundle)

    isa: list[tuple[str, str]] = []
    for cat in data["categories"]:
        isa += [(cat["id"], sup) for sup in cat.get("isa", [])]
    for category, members in data["concepts"].items():
        isa += [(_concept_id(en), category) for _ru, en in members]
    teach_isa(state, lattice_id, isa)

    teach_affords(state, lattice_id, [(c["id"], r) for c in data["categories"] for r in c.get("affords", [])])
    for r in data.get("relations", []):
        teach_relation(state, lattice_id, r["rel"], arg1=r["arg1"], arg2=r["arg2"])
    teach_parts(state, lattice_id, [tuple(p) for p in data.get("parts", [])])
    return {
        "concepts": len(pairs),
        "categories": len(data["categories"]),
        "relations": len(data.get("relations", [])),
        "parts": len(data.get("parts", [])),
    }


# --------------------------------------------------------------------------- #
# read / infer
# --------------------------------------------------------------------------- #
def isa_closure(state: dict, lattice_id: str, concept: str) -> set[str]:
    """All super-types of ``concept`` (transitive), including itself."""
    prefix = lambda c: f"{c}|{_ISA}|"  # noqa: E731
    edges = _edges(state, lattice_id)
    seen = {concept}
    frontier = [concept]
    while frontier:
        cur = frontier.pop()
        p = prefix(cur)
        for e in edges:
            if e.startswith(p):
                sup = e[len(p):]
                if sup and sup not in seen:
                    seen.add(sup)
                    frontier.append(sup)
    return seen


def affordances_of(state: dict, lattice_id: str, concept: str) -> set[str]:
    """Roles afforded by any type in ``concept``'s isa-closure (inherited capabilities)."""
    edges = _edges(state, lattice_id)
    roles: set[str] = set()
    for typ in isa_closure(state, lattice_id, concept):
        p = f"{typ}|{_AFFORDS}|"
        roles |= {e[len(p):] for e in edges if e.startswith(p)}
    return roles


def relation_roles(state: dict, lattice_id: str, rel: str) -> tuple[str | None, str | None]:
    edges = _edges(state, lattice_id)
    def one(slot: str) -> str | None:
        p = f"{rel}|{slot}|"
        hits = [e[len(p):] for e in edges if e.startswith(p)]
        return hits[0] if hits else None
    return one("arg1"), one("arg2")


def concept_of(state: dict, lattice_id: str, word: str) -> str | None:
    """Resolve a surface word (any language) to its concept via names edges; pass a
    concept id (contains '.') through unchanged.

    When a word names several concepts (synonyms from a large glossary), prefer the one
    we have a TYPED model of — a concept with an ``isa`` edge — so «мясо» resolves to
    the ontology's ``lex.meat`` rather than an untyped synonym."""
    if "." in word and " " not in word:
        return word
    hits = concepts_for_term(state, lattice_id, word)
    if not hits:
        return None
    edges = _edges(state, lattice_id)
    typed = [c for c in hits if any(e.startswith(f"{c}|{_ISA}|") for e in edges)]
    return (typed or hits)[0]


def validate(state: dict, lattice_id: str, rel: str, x: str, y: str) -> dict[str, Any]:
    """Validate ``rel(x, y)`` against the affordance/constraint network. Cross-lingual:
    x/y may be surface words in either language or concept ids."""
    cx, cy = concept_of(state, lattice_id, x), concept_of(state, lattice_id, y)
    if rel == _HAS_PART:  # mereology: asserted fact (inherited), not an affordance check
        ok = cx is not None and cy is not None and cy in parts_of(state, lattice_id, cx)
        return {"valid": bool(ok), "relation": rel, "x_concept": cx, "y_concept": cy, "reason": "ok" if ok else "not_a_part"}
    r1, r2 = relation_roles(state, lattice_id, rel)
    if cx is None or cy is None:
        return {"valid": False, "reason": "unknown_concept", "relation": rel, "x": x, "y": y, "x_concept": cx, "y_concept": cy}
    if r1 is None or r2 is None:
        return {"valid": False, "reason": "unknown_relation", "relation": rel, "x_concept": cx, "y_concept": cy}
    ax, ay = affordances_of(state, lattice_id, cx), affordances_of(state, lattice_id, cy)
    ok1, ok2 = r1 in ax, r2 in ay
    return {
        "valid": bool(ok1 and ok2),
        "relation": rel,
        "x_concept": cx,
        "y_concept": cy,
        "needs": {"arg1": r1, "arg2": r2},
        "arg1_ok": ok1,
        "arg2_ok": ok2,
        "reason": "ok" if (ok1 and ok2) else f"missing:{'' if ok1 else r1}{'' if ok2 else ('/' + r2)}",
    }


def names_of(state: dict, lattice_id: str, concept: str) -> dict[str, list[str]]:
    """Surfaces that name ``concept``, split by script — {'ru': [...], 'en': [...]}."""
    from casa.curriculum.translate import _name_edges, script_of

    prefix = f"{concept}|names|lang.word."
    out: dict[str, list[str]] = {"ru": [], "en": []}
    for e in _name_edges(state, lattice_id):
        if e.startswith(prefix):
            w = e[len(prefix):]
            out["ru" if script_of(w) == "cyrl" else "en"].append(w)
    return {k: sorted(set(v)) for k, v in out.items()}


def _node(state: dict, lattice_id: str, concept: str) -> dict[str, Any]:
    return {
        "concept": concept,
        "types": sorted(isa_closure(state, lattice_id, concept) - {concept}),
        "affords": sorted(affordances_of(state, lattice_id, concept)),
        "names": names_of(state, lattice_id, concept),
    }


def relation_map(state: dict, lattice_id: str, rel: str, x: str, y: str) -> dict[str, Any]:
    """Build an auditable meaning map for ``rel(x, y)``: two concept nodes (with their
    types, affordances and names in both languages) and the typed, checked edge between
    them. Built on CONCEPTS, so it is identical whether x/y are given in Russian or
    English — the language-independent «карта связей»."""
    cx, cy = concept_of(state, lattice_id, x), concept_of(state, lattice_id, y)
    v = validate(state, lattice_id, rel, x, y)
    return {
        "relation": rel,
        "valid": v["valid"],
        "reason": v.get("reason"),
        "subject": _node(state, lattice_id, cx) if cx else None,
        "object": _node(state, lattice_id, cy) if cy else None,
        "edge": {"rel": rel, "src": cx, "dst": cy, "satisfied": v["valid"], "needs": v.get("needs")},
    }


def render_map(m: dict[str, Any]) -> str:
    """One-line bilingual rendering of a relation map."""
    def label(node: dict[str, Any] | None) -> str:
        if not node:
            return "?"
        nm = node["names"]
        ru = nm["ru"][0] if nm["ru"] else node["concept"]
        en = nm["en"][0] if nm["en"] else node["concept"]
        return f"{ru}/{en}"

    mark = "✓" if m["valid"] else "✗"
    return f"{mark} [{label(m['subject'])}] --{m['relation']}--> [{label(m['object'])}]  ({m.get('reason')})"


# --------------------------------------------------------------------------- #
# held-out gate (generalisation via inheritance + negative control + ablation)
# --------------------------------------------------------------------------- #
def gate_concept_net(
    state: dict,
    lattice_id: str,
    valid_cases: list[tuple[str, str, str]],
    invalid_cases: list[tuple[str, str, str]],
) -> dict[str, Any]:
    """Verify held-out combinations validate via inheritance, category errors are
    rejected (negative control), and ablating the affords edges collapses validation.

    Cases are ``(relation, x, y)`` with x/y surface words or concept ids. The ontology
    (isa + affords + relation constraints) must be taught into ``state`` already.
    """
    from casa.prisms.memory.f0_stack import decode_f0_lattice, weaken_graph_edge

    pos = sum(validate(state, lattice_id, r, x, y)["valid"] for r, x, y in valid_cases)
    neg = sum(not validate(state, lattice_id, r, x, y)["valid"] for r, x, y in invalid_cases)
    valid_rate = pos / len(valid_cases) if valid_cases else 0.0
    negative_control_passed = neg == len(invalid_cases)

    # ablation: drop every affordance AND mereology edge -> nothing can be confirmed
    lat = _lattices(state).get(lattice_id)
    edges = decode_f0_lattice(lat).get("edges") or [] if lat else []
    for rel in (_AFFORDS, _HAS_PART):
        for e in [e for e in edges if f"|{rel}|" in e]:
            src, _, dst = e.split("|", 2)
            weaken_graph_edge(_lattices(state), lattice_id, src, rel, dst)
    ablation_breaks = not any(validate(state, lattice_id, r, x, y)["valid"] for r, x, y in valid_cases)

    passed = bool(
        len(valid_cases) >= 3
        and valid_rate >= 0.9
        and negative_control_passed
        and ablation_breaks
    )
    return {
        "passed": passed,
        "valid_cases": len(valid_cases),
        "invalid_cases": len(invalid_cases),
        "valid_pass_rate": round(valid_rate, 3),
        "negative_control_passed": negative_control_passed,
        "ablation_breaks_validation": ablation_breaks,
    }
