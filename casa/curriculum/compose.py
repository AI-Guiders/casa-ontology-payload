#!/usr/bin/env python3
"""Generative composition — produce English forms/phrases the field was never taught.

Two rule kinds, both stored AS FIELD EDGES and applied by reading them back, so the
rule lives in the field (not in Python). Ablating the edge breaks production, which
is what makes the held-out gate honest.

  * morphology (``suffix`` rule): induce the productive suffix from training pairs
    (English regular plural ``cat -> cats``) and apply it to UNSEEN stems. A pure
    memoriser fails the held-out nouns; an induced rule passes them.

  * syntax (``order`` rule): store an ordered slot list (English ``adj noun``) and
    realise a phrase by filling the slots in the field's order — combined with the
    glossary, this composes an English noun phrase from two Russian words that were
    never co-presented.

Honest scope: regular ``-s`` plural only (``box->boxes`` / ``baby->babies`` /
irregulars are not this rule) and fixed-order phrases. Productive over the lexicon,
deterministic, no hallucination — the same ceiling as the glossary: it composes
forms, it does not understand sentences.
"""

from __future__ import annotations

from typing import Any

from casa.curriculum.translate import translate_term

_SUFFIX_REL = "suffix"
_SUFFIX_DST = "lang.morph.suffix."
_ORDER_REL = "order"
_SLOT = "lang.slot."


# --------------------------------------------------------------------------- #
# induction (the "generator": derive a rule from examples)
# --------------------------------------------------------------------------- #
def induce_suffix(pairs: list[tuple[str, str]]) -> str | None:
    """Longest suffix ``S`` such that every ``base -> form`` is ``base + S``.

    Returns None if the pairs are not a single regular append rule (e.g. mixed
    ``-s``/``-es`` or stem changes) — the rule honestly declines rather than guess.
    """
    suffixes: set[str] = set()
    for base, form in pairs:
        base, form = str(base), str(form)
        if not form.startswith(base) or len(form) <= len(base):
            return None
        suffixes.add(form[len(base):])
    if len(suffixes) != 1:
        return None
    return next(iter(suffixes))


# --------------------------------------------------------------------------- #
# rule storage / read-back (the rule lives on the field)
# --------------------------------------------------------------------------- #
def _lattices(state: dict) -> dict:
    from casa.prisms.memory.memory_prisms import memory_lattices

    return memory_lattices(state)


def _edges(state: dict, lattice_id: str) -> list[str]:
    from casa.prisms.memory.f0_stack import decode_f0_lattice

    lat = _lattices(state).get(lattice_id)
    if not lat:
        return []
    return list(decode_f0_lattice(lat).get("edges") or [])


def teach_suffix_rule(
    state: dict, lattice_id: str, rule_id: str, pairs: list[tuple[str, str]], *, copies: int = 4
) -> dict[str, Any]:
    """Induce the suffix from ``pairs`` and mint ``rule_id|suffix|lang.morph.suffix.<S>``."""
    from casa.prisms.memory.f0_stack import strengthen_graph_edge

    suffix = induce_suffix(pairs)
    if suffix is None:
        return {"rule_id": rule_id, "induced": None, "stored": False}
    dst = f"{_SUFFIX_DST}{suffix}"
    stored = strengthen_graph_edge(_lattices(state), lattice_id, rule_id, _SUFFIX_REL, dst, copies=copies)
    return {"rule_id": rule_id, "induced": suffix, "stored": bool(stored)}


def read_suffix_rule(state: dict, lattice_id: str, rule_id: str) -> str | None:
    """Read the stored suffix for ``rule_id`` from the field (None if absent/ablated)."""
    prefix = f"{rule_id}|{_SUFFIX_REL}|{_SUFFIX_DST}"
    for edge in _edges(state, lattice_id):
        if edge.startswith(prefix):
            return edge[len(prefix):]
    return None


def apply_suffix_rule(state: dict, lattice_id: str, rule_id: str, stem: str) -> str | None:
    """Generate ``stem + suffix`` using the field-stored rule (None if no rule)."""
    suffix = read_suffix_rule(state, lattice_id, rule_id)
    return f"{stem}{suffix}" if suffix is not None else None


def teach_order_rule(
    state: dict, lattice_id: str, rule_id: str, slot_order: list[str], *, copies: int = 4
) -> dict[str, Any]:
    """Store an ordered slot list as ``rule_id|order|lang.slot.<name>@<i>`` edges."""
    from casa.prisms.memory.f0_stack import strengthen_graph_edge

    lats = _lattices(state)
    for i, slot in enumerate(slot_order):
        strengthen_graph_edge(lats, lattice_id, rule_id, _ORDER_REL, f"{_SLOT}{slot}@{i}", copies=copies)
    return {"rule_id": rule_id, "order": list(slot_order), "stored": True}


def read_order_rule(state: dict, lattice_id: str, rule_id: str) -> list[str]:
    """Read the slot order for ``rule_id`` from the field, sorted by index."""
    prefix = f"{rule_id}|{_ORDER_REL}|{_SLOT}"
    indexed: list[tuple[int, str]] = []
    for edge in _edges(state, lattice_id):
        if not edge.startswith(prefix):
            continue
        tail = edge[len(prefix):]
        slot, _, idx = tail.rpartition("@")
        if idx.isdigit():
            indexed.append((int(idx), slot))
    return [slot for _, slot in sorted(indexed)]


def apply_order_rule(state: dict, lattice_id: str, rule_id: str, fillers: dict[str, str]) -> str | None:
    """Realise a phrase by filling slots in the field's stored order (None if no rule)."""
    order = read_order_rule(state, lattice_id, rule_id)
    if not order or any(slot not in fillers for slot in order):
        return None
    return " ".join(fillers[slot] for slot in order)


def compose_en_np(state: dict, lattice_id: str, ru_adj: str, ru_noun: str, *, rule_id: str = "lang.phrase.np.en") -> str | None:
    """Compose an English noun phrase from two Russian words (glossary + order rule)."""
    adj = translate_term(state, lattice_id, ru_adj, to_script="latn")
    noun = translate_term(state, lattice_id, ru_noun, to_script="latn")
    if not adj or not noun:
        return None
    return apply_order_rule(state, lattice_id, rule_id, {"adj": adj[0], "noun": noun[0]})


# --------------------------------------------------------------------------- #
# held-out gate (anti-tautology: generalisation + negative control + ablation)
# --------------------------------------------------------------------------- #
def gate_suffix_rule(
    state: dict,
    lattice_id: str,
    rule_id: str,
    pairs: list[tuple[str, str]],
    *,
    held_out_ratio: float = 0.4,
    pass_ratio: float = 0.8,
    min_held_out: int = 3,
) -> dict[str, Any]:
    """Induce the rule from a TRAIN split, verify it generates the HELD-OUT plurals.

    Reports: held-out pass rate, a negative control (wrong-suffix labels must NOT
    pass), and an ablation check (removing the field edge must break production).
    ``passed`` requires real generalisation AND field-dependence.
    """
    from casa.prisms.memory.f0_stack import weaken_graph_edge

    n_held = max(min_held_out, round(len(pairs) * held_out_ratio))
    held_out = pairs[:n_held]
    train = pairs[n_held:]
    if len(train) < 1 or len(held_out) < min_held_out:
        return {"passed": False, "reason": "insufficient_pairs", "rule_id": rule_id}

    rep = teach_suffix_rule(state, lattice_id, rule_id, train)
    if not rep["stored"]:
        return {"passed": False, "reason": "no_rule_induced", "rule_id": rule_id, **rep}

    # generalisation: the rule (learned from TRAIN) must produce HELD-OUT forms
    passes = [apply_suffix_rule(state, lattice_id, rule_id, b) == f for b, f in held_out]
    held_rate = sum(passes) / len(passes)

    # negative control: relabel held-out targets to a WRONG suffix — must NOT pass
    neg = [apply_suffix_rule(state, lattice_id, rule_id, b) == f"{b}{rep['induced']}X" for b, _ in held_out]
    negative_control_passed = not any(neg)

    # ablation: remove the field edge, production must collapse (proves field-dependence)
    dst = f"{_SUFFIX_DST}{rep['induced']}"
    weaken_graph_edge(_lattices(state), lattice_id, rule_id, _SUFFIX_REL, dst)
    ablated = [apply_suffix_rule(state, lattice_id, rule_id, b) for b, _ in held_out]
    ablation_breaks = all(a is None for a in ablated)
    # restore the rule
    teach_suffix_rule(state, lattice_id, rule_id, train)

    passed = bool(
        len(held_out) >= min_held_out
        and held_rate >= pass_ratio
        and negative_control_passed
        and ablation_breaks
    )
    return {
        "passed": passed,
        "rule_id": rule_id,
        "induced": rep["induced"],
        "train": len(train),
        "held_out": len(held_out),
        "held_out_pass_rate": round(held_rate, 3),
        "negative_control_passed": negative_control_passed,
        "ablation_breaks_production": ablation_breaks,
    }
