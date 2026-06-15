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
_CLAUSE_REL = "clause"
_CLAUSE_SEP = "~"  # edge dst must not contain '|'; '~' separates clause fields


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
# class-conditioned rules (morphophonology: suffix choice depends on the stem)
# --------------------------------------------------------------------------- #
def _transform(base: str, form: str) -> tuple[int, str]:
    """Edit from ``base`` to ``form`` as (chars to cut from end, string to add).

    Returns ``(cut, add, double)``: cut chars from the end, then (if ``double``) a
    copy of the final char, then ``add``.

    ``cat -> cats`` = (0, 's', False); ``baby -> babies`` = (1, 'ies', False) — found
    via the longest common prefix; ``big -> bigger`` = (0, 'er', True) — the suffix
    starts with a copy of the stem's last letter (consonant doubling).
    """
    n = 0
    for a, b in zip(base.lower(), form.lower()):
        if a != b:
            break
        n += 1
    cut, tail = len(base) - n, form[n:]
    if cut == 0 and tail and base and tail[0].lower() == base[-1].lower():
        return 0, tail[1:], True  # gemination: copy final char, then the rest
    return cut, tail, False


def _apply_transform(stem: str, cut: int, add: str, double: bool = False) -> str:
    s = stem[: len(stem) - cut] if cut else stem
    if double and s:
        s = s + s[-1]
    return s + add


_VOWELS = set("aeiou") | set("аеёиоуыэюя")  # given primitive: vowels (Latin + Cyrillic)
_VELAR = set("кгхжшчщ")  # given primitive: the Russian velar/hushing class (ы/и spelling)


def _matches(stem: str, pattern: str) -> bool:
    """Match a stem's tail against a pattern of literals + ``C``/``V``/``K`` classes.

    ``''`` matches anything (the default clause); ``Cy`` is a consonant+y (``baby``,
    not ``day``); ``Kа`` is a velar/hushing consonant + а (``книга``, ``нога``, not
    ``рыба``) — the seam Russian feminine declension turns on.
    """
    s = stem.lower()
    if len(s) < len(pattern):
        return False
    for i in range(1, len(pattern) + 1):
        tok, ch = pattern[-i], s[-i]
        if tok == "C":
            if not (ch.isalpha() and ch not in _VOWELS):
                return False
        elif tok == "V":
            if ch not in _VOWELS:
                return False
        elif tok == "K":
            if ch not in _VELAR:
                return False
        elif ch != tok:
            return False
    return True


def _candidate_patterns(stem: str) -> list[str]:
    """Patterns for a stem's tail, GENERAL first (fewer literals, shorter) so the
    learner prefers the broadest condition that still separates the class."""
    from itertools import product

    def char_opts(ch: str) -> list[str]:
        if ch in _VOWELS:
            return ["V", ch]
        if ch in _VELAR:
            return ["C", "K", ch]  # general consonant, velar/hushing subclass, literal
        return ["C", ch]

    def specificity(p: str) -> int:  # class < velar-class < literal
        return sum({"C": 0, "V": 0, "K": 1}.get(c, 2) for c in p)

    s = stem.lower()
    pats: set[str] = set()
    for length in range(1, min(len(s), 4) + 1):
        for combo in product(*[char_opts(ch) for ch in s[-length:]]):
            pats.add("".join(combo))
    return sorted(pats, key=lambda p: (len(p), specificity(p), p))


def _induce_condition(group: list[str], others: list[str]) -> list[str] | None:
    """Broadest tail-patterns that pick out ``group`` without matching any ``others``.

    Prefers a single general pattern (``Cy`` for the whole consonant+y class) over
    memorising each bigram, but stays literal where no class generalises (the
    sibilants ``x``/``s``/``z``/``sh``/``ch`` that take ``-es``).
    """
    conds: set[str] = set()
    for s in group:
        chosen = next(
            (p for p in _candidate_patterns(s) if _matches(s, p) and not any(_matches(o, p) for o in others)),
            None,
        )
        if chosen is None:
            return None  # cannot separate this class from the rest on the evidence
        conds.add(chosen)
    return sorted(conds, key=lambda x: (-len(x), x))


def induce_conditioned_rule(pairs: list[tuple[str, str]]) -> list[tuple[str, int, str, bool]] | None:
    """Induce an ordered decision list of ``(ending, cut, add, double)`` clauses.

    The most frequent transform becomes the default clause (``ending == ''``); every
    other transform gets the conditions that separate it from the rest. Returns None
    if some class cannot be separated on the given evidence. Empty ``ending`` matches
    any stem and is applied last.
    """
    groups: dict[tuple[int, str, bool], list[str]] = {}
    for base, form in pairs:
        groups.setdefault(_transform(str(base), str(form)), []).append(str(base))
    if not groups:
        return None
    default_tf = max(groups, key=lambda t: (len(groups[t]), t))
    clauses: list[tuple[str, int, str, bool]] = []
    for tf, stems in groups.items():
        if tf == default_tf:
            continue
        others = [s for g, ss in groups.items() if g != tf for s in ss]
        conds = _induce_condition(stems, others)
        if conds is None:
            return None
        for ending in conds:
            clauses.append((ending, tf[0], tf[1], tf[2]))
    clauses.sort(key=lambda c: (-len(c[0]), c[0]))  # specific endings first
    clauses.append(("", default_tf[0], default_tf[1], default_tf[2]))  # default last
    return clauses


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


def teach_conditioned_rule(
    state: dict, lattice_id: str, rule_id: str, pairs: list[tuple[str, str]], *, copies: int = 4
) -> dict[str, Any]:
    """Induce a class-conditioned rule from ``pairs`` and mint one edge per clause."""
    from casa.prisms.memory.f0_stack import strengthen_graph_edge

    clauses = induce_conditioned_rule(pairs)
    if clauses is None:
        return {"rule_id": rule_id, "clauses": None, "stored": False}
    lats = _lattices(state)
    for ending, cut, add, double in clauses:
        strengthen_graph_edge(lats, lattice_id, rule_id, _CLAUSE_REL, _clause_dst(ending, cut, add, double), copies=copies)
    return {"rule_id": rule_id, "clauses": clauses, "stored": True}


def _clause_dst(ending: str, cut: int, add: str, double: bool) -> str:
    return _CLAUSE_SEP.join((ending or "_", str(cut), add or "_", "1" if double else "0"))


def read_conditioned_rule(state: dict, lattice_id: str, rule_id: str) -> list[tuple[str, int, str, bool]]:
    """Read the clause decision list for ``rule_id`` from the field (ordered)."""
    prefix = f"{rule_id}|{_CLAUSE_REL}|"
    clauses: list[tuple[str, int, str, bool]] = []
    for edge in _edges(state, lattice_id):
        if not edge.startswith(prefix):
            continue
        parts = edge[len(prefix):].split(_CLAUSE_SEP)
        if len(parts) != 4 or not parts[1].isdigit():
            continue
        ending = "" if parts[0] == "_" else parts[0]
        add = "" if parts[2] == "_" else parts[2]
        clauses.append((ending, int(parts[1]), add, parts[3] == "1"))
    # most specific first (longer, more literals), default ('') last
    clauses.sort(key=lambda c: (-len(c[0]), -sum(ch not in "CV" for ch in c[0]), c[0]))
    return clauses


def apply_conditioned_rule(state: dict, lattice_id: str, rule_id: str, stem: str) -> str | None:
    """Generate the inflected form of ``stem`` using the field-stored decision list."""
    clauses = read_conditioned_rule(state, lattice_id, rule_id)
    if not clauses:
        return None
    for ending, cut, add, double in clauses:
        if ending == "" or _matches(stem, ending):
            return _apply_transform(stem, cut, add, double)
    return None


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


NP_RULE = "lang.np.en"
_NP_ORDER = ["det", "num", "adj", "noun"]  # the two big cats


def teach_np_order(state: dict, lattice_id: str, *, rule_id: str = NP_RULE) -> dict[str, Any]:
    """Store the noun-phrase slot order (det, number, adjective, noun) on the field."""
    return teach_order_rule(state, lattice_id, rule_id, _NP_ORDER)


def compose_np(
    state: dict,
    lattice_id: str,
    *,
    noun: str,
    adj: str | None = None,
    number: str | None = None,
    determiner: str | None = None,
    plural: bool = False,
    lang_in: str = "ru",
    plural_rule: str = "lang.rule.plural.en",
    rule_id: str = NP_RULE,
) -> tuple[str | None, bool]:
    """Build a noun phrase and report its number. A ``number`` other than one forces
    plural; the noun is pluralised by the learned plural rule. Returns ``(text, is_plural)``
    — ``(None, False)`` if a word is unknown or the NP order rule is absent."""
    def en(word: str | None) -> str | None:
        if word is None:
            return None
        if lang_in == "en":
            return word
        hits = translate_term(state, lattice_id, word, to_script="latn")
        return hits[0] if hits else None

    n_en = en(noun)
    if not n_en:
        return None, False
    a_en = en(adj)
    if adj and not a_en:
        return None, False
    num_en = en(number)
    if number and not num_en:
        return None, False

    is_plural = bool(plural or (num_en and num_en != "one"))
    noun_form = (apply_conditioned_rule(state, lattice_id, plural_rule, n_en) or f"{n_en}s") if is_plural else n_en

    fillers = {"det": determiner, "num": num_en, "adj": a_en, "noun": noun_form}
    order = read_order_rule(state, lattice_id, rule_id)  # field-stored; absent -> decline
    if not order:
        return None, False
    words = [fillers[slot] for slot in order if fillers.get(slot)]
    if not words:
        return None, False
    return " ".join(words), is_plural


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


def gate_conditioned_rule(
    state: dict,
    lattice_id: str,
    rule_id: str,
    pairs: list[tuple[str, str]],
    *,
    held_out_ratio: float = 0.3,
    pass_ratio: float = 0.9,
    min_held_out: int = 3,
) -> dict[str, Any]:
    """Gate a class-conditioned rule: stratified held-out (every class trained AND
    tested), negative control, and ablation. Catches over-general conditions — a
    clause learned too broadly mis-inflects a held-out word of another class and the
    held-out rate drops below ``pass_ratio``.
    """
    from casa.prisms.memory.f0_stack import weaken_graph_edge

    groups: dict[tuple[int, str], list[tuple[str, str]]] = {}
    for b, f in pairs:
        groups.setdefault(_transform(str(b), str(f)), []).append((str(b), str(f)))
    step = max(2, round(1 / held_out_ratio)) if held_out_ratio > 0 else 0
    train: list[tuple[str, str]] = []
    held: list[tuple[str, str]] = []
    for items in groups.values():
        # stride across the group so held-out spreads over sub-classes (endings),
        # never removing the last witness of a sibilant ending
        chosen = set(range(0, len(items), step)) if step and len(items) >= 2 else set()
        held += [it for i, it in enumerate(items) if i in chosen]
        train += [it for i, it in enumerate(items) if i not in chosen]
    if len(held) < min_held_out or not train:
        return {"passed": False, "reason": "insufficient_pairs", "rule_id": rule_id}

    rep = teach_conditioned_rule(state, lattice_id, rule_id, train)
    if not rep["stored"]:
        return {"passed": False, "reason": "no_rule_induced", "rule_id": rule_id}

    passes = [apply_conditioned_rule(state, lattice_id, rule_id, b) == f for b, f in held]
    held_rate = sum(passes) / len(passes)
    neg = [apply_conditioned_rule(state, lattice_id, rule_id, b) == f"{f}X" for b, f in held]
    negative_control_passed = not any(neg)

    for ending, cut, add, double in rep["clauses"]:
        weaken_graph_edge(_lattices(state), lattice_id, rule_id, _CLAUSE_REL, _clause_dst(ending, cut, add, double))
    ablated = [apply_conditioned_rule(state, lattice_id, rule_id, b) for b, _ in held]
    ablation_breaks = all(a is None for a in ablated)
    teach_conditioned_rule(state, lattice_id, rule_id, train)  # restore

    passed = bool(
        len(held) >= min_held_out
        and held_rate >= pass_ratio
        and negative_control_passed
        and ablation_breaks
    )
    return {
        "passed": passed,
        "rule_id": rule_id,
        "classes": len(groups),
        "clauses": rep["clauses"],
        "train": len(train),
        "held_out": len(held),
        "held_out_pass_rate": round(held_rate, 3),
        "negative_control_passed": negative_control_passed,
        "ablation_breaks_production": ablation_breaks,
    }
