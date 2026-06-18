#!/usr/bin/env python3
"""Domain parser — turn a controlled clause into a meaning graph (text -> fingerprint).

This is the last rung: free-ish text to the canonical concept graph. Honest scope — a
RULE-BASED parser for simple clauses in the domain, not open-domain understanding:

  locative:    [figure] (positional verb)? PREP [ground] (PREP [ground])*
               «яблоко на столе», «яблоко лежит на столе», «на столе яблоко»,
               «яблоко на столе у окна»
  transitive:  [subject] VERB [object]      «собака ест мясо», «студент читает книгу»

Words are resolved to concepts by exact name, then by a domain stem heuristic (столе ->
стол -> lex.table) so inflected forms work. The relation comes from the preposition or
verb (synonyms collapse via normalize_relation). Because the output is a concept graph,
all three phrasings of one situation parse to the SAME triples — and hence the same
fingerprint. Role assignment uses preposition position + word order; it is deliberately
simple and domain-scoped.
"""

from __future__ import annotations

import re
from typing import Any

from casa.curriculum.concept_net import concept_of, meaning_graph
from casa.curriculum.situation import PREDICATE_RELATION, fingerprint, normalize_relation

_PREPS = {"на", "в", "у", "около", "рядом", "под", "над", "on", "in", "near", "by", "under", "inside", "beside"}
_POSITIONAL = {"лежит", "стоит", "находится", "лежать", "стоять", "находиться", "висит",
               "lies", "stands", "sits", "is", "hangs",
               "сделан", "сделана", "сделано", "сделаны", "made"}  # made_of copula
_NEG = {"не", "нет", "ни", "not", "don't", "do not", "doesn't", "no", "never"}  # negation markers


def _tokens(text: str) -> list[str]:
    return re.findall(r"[\wЀ-ӿ]+", str(text or "").lower(), flags=re.UNICODE)


def _typed_concepts(state: dict, lattice_id: str) -> set[str]:
    """Concepts that are IN the ontology (appear as the source of an isa edge)."""
    from casa.prisms.memory.f0_stack import decode_f0_lattice
    from casa.prisms.memory.memory_prisms import memory_lattices

    lat = memory_lattices(state).get(lattice_id)
    edges = decode_f0_lattice(lat).get("edges") or [] if lat else []
    return {e.split("|isa|")[0] for e in edges if "|isa|" in e}


def _name_index(state: dict, lattice_id: str) -> list[tuple[str, str]]:
    """(russian surface, ontology-concept) pairs, longest surface first — for stem
    resolution. Restricted to concepts in the ontology so stem matches don't drift into
    untyped synonyms from a large merged glossary (столе -> стол/table, not столб/post)."""
    from casa.curriculum.translate import _name_edges, script_of

    typed = _typed_concepts(state, lattice_id)
    pre = "|names|lang.word."
    out: list[tuple[str, str]] = []
    for e in _name_edges(state, lattice_id):
        concept, _, surface = e.partition(pre)
        if surface and concept in typed and script_of(surface) == "cyrl":
            out.append((surface, concept))
    return sorted(set(out), key=lambda p: -len(p[0]))


def resolve_token(state: dict, lattice_id: str, token: str, names: list[tuple[str, str]] | None = None) -> str | None:
    """Resolve a (possibly inflected) word to a concept: exact name, then lemma match.

    Lemma match picks the surface that is the token's base form: the longest common
    prefix wins, then the shortest surface — so «столе» resolves to «стол» (lemma,
    differs by an ending), not «столб» (a different, longer word)."""
    c = concept_of(state, lattice_id, token)
    if c:
        return c
    best: str | None = None
    best_key: tuple[int, int] | None = None
    for surface, concept in names if names is not None else _name_index(state, lattice_id):
        n = min(len(token), len(surface))
        lcp = 0
        while lcp < n and token[lcp] == surface[lcp]:
            lcp += 1
        if lcp < 3 or len(surface) - lcp > 1 or len(token) - lcp > 3:
            continue  # surface must be the lemma (same prefix, differs only in the tail)
        key = (-lcp, len(surface))  # longest shared prefix, then shortest lemma
        if best_key is None or key < best_key:
            best, best_key = concept, key
    return best


def parse_situation(
    state: dict, lattice_id: str, text: str
) -> tuple[list[tuple[str, str, str]], dict[str, list[str]], str, dict[str, int]]:
    """Parse a controlled clause into triples, adjective attributes, polarity, and counts.

    Returns ``(triples, attrs, polarity, counts)``: ``attrs[cid]`` are attribute ids
    («red») and ``counts[cid]`` is the quantity («два файла» → 2) modifying that concept —
    both bind to the next noun; ``polarity`` is ``"neg"`` for a negated clause, else
    ``"pos"``."""
    from casa.curriculum.attributes import attr_of_token
    from casa.curriculum.quantity import number_of_token

    names = _name_index(state, lattice_id)
    seq: list[tuple[str, Any]] = []  # ('prep'|'verb'|'noun'|'adj'|'num', payload) in order
    polarity = "pos"
    for tok in _tokens(text):
        if tok in _NEG:
            polarity = "neg"  # negation marker — scopes the clause's relation
        elif tok in _PREPS:
            seq.append(("prep", normalize_relation(tok)))
        elif tok in _POSITIONAL:
            continue  # positional copula — the preposition carries the relation
        elif tok in PREDICATE_RELATION and tok not in _PREPS:
            seq.append(("verb", normalize_relation(tok)))
        elif (num := number_of_token(tok)) is not None:
            seq.append(("num", num))
        elif (aid := attr_of_token(tok)) is not None:
            seq.append(("adj", aid))
        else:
            cid = resolve_token(state, lattice_id, tok, names)
            if cid:
                seq.append(("noun", cid))

    # bind each adjective and number to the next noun in sequence
    attrs: dict[str, list[str]] = {}
    counts: dict[str, int] = {}
    pending: list[str] = []
    pending_count: int | None = None
    for kind, payload in seq:
        if kind == "adj":
            pending.append(payload)
        elif kind == "num":
            pending_count = payload
        elif kind == "noun":
            if pending:
                attrs.setdefault(payload, [])
                attrs[payload].extend(a for a in pending if a not in attrs[payload])
            if pending_count is not None:
                counts[payload] = pending_count
            pending, pending_count = [], None

    nouns = [(i, p) for i, (k, p) in enumerate(seq) if k == "noun"]
    preps = [(i, p) for i, (k, p) in enumerate(seq) if k == "prep"]
    verbs = [(i, p) for i, (k, p) in enumerate(seq) if k == "verb"]

    if preps:  # locative: each preposition links the noun before it to the noun after it
        triples: list[tuple[str, str, str]] = []
        for pi, rel in preps:
            before = [c for ni, c in nouns if ni < pi]
            after = [c for ni, c in nouns if ni > pi]
            if not after:
                continue
            ground = after[0]
            figure = before[-1] if before else (after[1] if len(after) > 1 else None)
            if figure:
                triples.append((rel, figure, ground))
        return triples, attrs, polarity, counts
    if verbs and len(nouns) >= 2:  # transitive S-V-O
        return [(verbs[0][1], nouns[0][1], nouns[1][1])], attrs, polarity, counts
    if verbs and len(nouns) == 1 and verbs[0][0] < nouns[0][0]:
        # imperative: a verb BEFORE its only noun, no subject — «открой файл» / «open the
        # file». The implicit agent is «you». (A noun before the verb is S-V, not a command.)
        return [(verbs[0][1], "lex.you", nouns[0][1])], attrs, polarity, counts
    return [], attrs, polarity, counts


def parse_triples(state: dict, lattice_id: str, text: str) -> list[tuple[str, str, str]]:
    """Parse a controlled clause into (relation, concept, concept) triples (concept ids)."""
    return parse_situation(state, lattice_id, text)[0]


def parse_graph(state: dict, lattice_id: str, text: str) -> dict[str, Any]:
    """Parse text and build its meaning graph, with adjective attributes and counts on the
    nodes and clause polarity on the edges (a negated clause marks ``polarity='neg'``)."""
    triples, attrs, polarity, counts = parse_situation(state, lattice_id, text)
    graph = meaning_graph(state, lattice_id, triples)
    for cid, aids in attrs.items():
        if cid in graph["nodes"]:
            graph["nodes"][cid]["attrs"] = aids
    for cid, n in counts.items():
        if cid in graph["nodes"]:
            graph["nodes"][cid]["count"] = n
    for edge in graph["edges"]:
        edge["polarity"] = polarity
    return graph


def parse_fingerprint(state: dict, lattice_id: str, text: str) -> dict[str, Any]:
    """Parse text all the way to its situation fingerprint."""
    return fingerprint(parse_graph(state, lattice_id, text))
