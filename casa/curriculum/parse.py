#!/usr/bin/env python3
"""Domain parser — turn a controlled clause into a meaning graph (text -> fingerprint).

This is the last rung: free-ish text to the canonical concept graph. Honest scope — a
RULE-BASED parser for simple clauses in the domain, not open-domain understanding:

  locative:    [figure] (positional verb)? PREP [ground] (PREP [ground])*
               «яблоко на столе», «яблоко лежит на столе», «на столе яблоко»,
               «яблоко на столе у окна»
  transitive:  [subject] VERB [object]      «собака ест мясо», «студент читает книгу»

Words are resolved to concepts by exact name, then by a domain stem heuristic (столе ->
стол -> concept.table) so inflected forms work. The relation comes from the preposition or
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

_PREPS = {"на", "в", "у", "около", "рядом", "под", "над", "on", "in", "near", "by", "under", "inside", "beside",
          "to", "into"}  # «to/into» — action destination
_POSITIONAL = {"лежит", "стоит", "находится", "лежать", "стоять", "находиться", "висит",
               "lies", "stands", "sits", "is", "hangs",
               "сделан", "сделана", "сделано", "сделаны", "made",  # made_of copula
               "than", "чем"}  # comparison connector («bigger than», «больше, чем»)
_NEG = {"не", "нет", "ни", "not", "don't", "do not", "doesn't", "no", "never"}  # negation markers
_AND = {"и", "and"}  # coordinator — distributes a role over conjuncts
_COPULA = {"is", "are"}  # English predicative copula — marks the next word as a state predicate


def _tokens(text: str) -> list[str]:
    return re.findall(r"[\wЀ-ӿ]+", str(text or "").lower(), flags=re.UNICODE)


def _typed_concepts(state: dict, lattice_id: str) -> set[str]:
    """Concepts that are IN the ontology (appear as the source of an isa edge)."""
    from casa.prisms.memory.f0_stack import decode_f0_lattice
    from casa.prisms.memory.memory_prisms import memory_lattices

    lat = memory_lattices(state).get(lattice_id)
    edges = decode_f0_lattice(lat).get("edges") or [] if lat else []
    return {e.split("|isa|")[0] for e in edges if "|isa|" in e}


_NAME_INDEX_CACHE: dict[tuple[int, str], list[tuple[str, str]]] = {}


def _name_index(state: dict, lattice_id: str) -> list[tuple[str, str]]:
    """(russian surface, ontology-concept) pairs, longest surface first — for stem
    resolution. Restricted to concepts in the ontology so stem matches don't drift into
    untyped synonyms from a large merged glossary (столе -> стол/table, not столб/post).

    Memoised per (state, lattice): the name edges don't change during a session (persisting
    a situation adds situation edges, not names), so repeated parses don't rescan the
    ontology — a large speedup for batch use (the reality-check, many chat turns)."""
    key = (id(state), lattice_id)
    cached = _NAME_INDEX_CACHE.get(key)
    if cached is not None:
        return cached
    from casa.curriculum.translate import _name_edges, script_of

    typed = _typed_concepts(state, lattice_id)
    pre = "|names|lang.word."
    out: list[tuple[str, str]] = []
    for e in _name_edges(state, lattice_id):
        concept, _, surface = e.partition(pre)
        if surface and concept in typed and script_of(surface) == "cyrl":
            out.append((surface, concept))
    result = sorted(set(out), key=lambda p: -len(p[0]))
    _NAME_INDEX_CACHE[key] = result
    return result


def _en_singulars(token: str) -> list[str]:
    """Candidate singulars of an English plural (files→file, boxes→box, parties→party)."""
    cands = []
    if token.endswith("ies") and len(token) > 4:
        cands.append(token[:-3] + "y")
    if token.endswith("es") and len(token) > 3:
        cands.append(token[:-2])
    if token.endswith("s") and len(token) > 2:
        cands.append(token[:-1])
    return cands


def resolve_token(state: dict, lattice_id: str, token: str, names: list[tuple[str, str]] | None = None) -> str | None:
    """Resolve a (possibly inflected) word to a concept: exact name, English plural lemma,
    then Russian stem match.

    Russian lemma match picks the surface that is the token's base form: the longest common
    prefix wins, then the shortest surface — so «столе» resolves to «стол» (lemma,
    differs by an ending), not «столб» (a different, longer word)."""
    from casa.curriculum.translate import script_of

    c = concept_of(state, lattice_id, token)
    if c:
        return c
    if script_of(token) == "latn":  # English plural -> singular («files» → concept.file)
        for cand in _en_singulars(token):
            c = concept_of(state, lattice_id, cand)
            if c:
                return c
        return None  # no Russian-stem matching for Latin tokens
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
) -> tuple[list[tuple[str, str, str]], dict[str, list[str]], str, dict[str, int], dict[str, dict]]:
    """Parse a controlled clause into triples, attributes, polarity, counts, and measures.

    Returns ``(triples, attrs, polarity, counts, measures)``: ``attrs[cid]`` are attribute
    ids («red»), ``counts[cid]`` a plain count («два файла» → 2), and ``measures[cid]`` a
    measure with a unit («5 мл воды» → {value:5, unit:'ml'}) — all bind to the next noun;
    ``polarity`` is ``"neg"`` for a negated clause, else ``"pos"``."""
    from casa.curriculum.attributes import COLOR_IDS, attr_of_token
    from casa.curriculum.quantity import number_of_token, unit_of_token
    from casa.curriculum.states import state_of_token

    names = _name_index(state, lattice_id)
    seq: list[tuple[str, Any]] = []  # ('prep'|'verb'|'noun'|'adj'|'num'|'unit'|'state', payload)
    polarity = "pos"
    copula = False  # saw an English copula «is/are» — the next state word is predicative
    for tok in _tokens(text):
        if tok in _NEG:
            polarity = "neg"  # negation marker — scopes the clause's relation
        elif tok in _AND:
            seq.append(("and", None))  # coordinator
        elif tok in _COPULA:
            copula = True  # «the file is open» — marks the following state predicate
        elif tok in _PREPS:
            seq.append(("prep", normalize_relation(tok)))
        elif tok in _POSITIONAL:
            continue  # positional copula — the preposition carries the relation
        elif (sid := state_of_token(tok)) is not None and (copula or tok not in PREDICATE_RELATION):
            seq.append(("state", sid))  # predicative state; an EN verb/adj clash («open») needs the copula
        elif tok in PREDICATE_RELATION and tok not in _PREPS:
            seq.append(("verb", normalize_relation(tok)))
        elif (num := number_of_token(tok)) is not None:
            seq.append(("num", num))
        elif (unit := unit_of_token(tok)) is not None:
            seq.append(("unit", unit))
        elif (aid := attr_of_token(tok)) is not None:
            seq.append(("adj", aid))
        else:
            cid = resolve_token(state, lattice_id, tok, names)
            if cid:
                seq.append(("noun", cid))

    # bind each adjective, number and measure to the next noun in sequence
    attrs: dict[str, list[str]] = {}
    counts: dict[str, int] = {}
    measures: dict[str, dict] = {}
    pending: list[str] = []
    pending_count: int | None = None
    pending_unit: str | None = None
    for kind, payload in seq:
        if kind == "adj":
            pending.append(payload)
        elif kind == "num":
            pending_count = payload
        elif kind == "unit":
            pending_unit = payload
        elif kind == "noun":
            if pending:
                attrs.setdefault(payload, [])
                attrs[payload].extend(a for a in pending if a not in attrs[payload])
            if pending_unit is not None:  # «5 мл воды» — a measure, not a plain count
                measures[payload] = {"value": pending_count or 1, "unit": pending_unit}
            elif pending_count is not None:
                counts[payload] = pending_count
            pending, pending_count, pending_unit = [], None, None

    nouns = [(i, p) for i, (k, p) in enumerate(seq) if k == "noun"]
    preps = [(i, p) for i, (k, p) in enumerate(seq) if k == "prep"]
    verbs = [(i, p) for i, (k, p) in enumerate(seq) if k == "verb"]
    has_and = any(k == "and" for k, _ in seq)
    # the head of a noun-noun compound differs by language: English head-LAST («icon file» →
    # file), Russian genitive head-FIRST («файл пиктограммы» → файл).
    is_ru = bool(re.search(r"[Ѐ-ӿ]", text))
    head = lambda ns: ns[0][1] if is_ru else ns[-1][1]  # noqa: E731

    # habitat: «кошка живёт в доме» — lives_in absorbs the following preposition (one edge,
    # not action+location), because a home is a habitat, not a container
    live = [i for i, (k, r) in enumerate(seq) if k == "verb" and r == "lives_in"]
    if live and preps:
        subj = [c for ni, c in nouns if ni < live[0]]
        habitat = [c for ni, c in nouns if ni > preps[0][0]]
        if subj and habitat:
            return [("lives_in", subj[-1], habitat[0])], attrs, polarity, counts, measures

    # action with a destination: «сохрани файл в папку» — a verb BEFORE a preposition. Two
    # edges: the action and the resultant location of its object («save»: in(file, folder)).
    if verbs and preps and verbs[0][0] < preps[0][0]:
        vp, vrel = verbs[0]
        pp, prel = preps[0]
        subj_nouns = [(ni, c) for ni, c in nouns if ni < vp]
        subject = subj_nouns[-1][1] if subj_nouns else "concept.you"
        obj_nouns = [(ni, c) for ni, c in nouns if vp < ni < pp]
        dest = [c for ni, c in nouns if ni > pp]
        if obj_nouns and dest:
            obj = head(obj_nouns)
            return [(vrel, subject, obj), (prel, obj, dest[0])], attrs, polarity, counts, measures

    if preps:  # locative: each preposition links the noun before it to the noun after it
        triples: list[tuple[str, str, str]] = []
        first_pi = preps[0][0]
        pre_first = [c for ni, c in nouns if ni < first_pi]
        # «X и Y на Z» — coordinated figures (only the single-prep case, to keep nesting safe)
        coord_figs = pre_first if (has_and and len(preps) == 1 and len(pre_first) >= 2) else None
        for pi, rel in preps:
            before = [c for ni, c in nouns if ni < pi]
            after = [c for ni, c in nouns if ni > pi]
            if not after:
                continue
            ground = after[0]
            if coord_figs is not None and pi == first_pi:
                figures = coord_figs
            elif before:
                figures = [before[-1]]  # closest noun before the prep is the figure
            else:
                figures = [after[1]] if len(after) > 1 else []
            triples += [(rel, fig, ground) for fig in figures]
        return triples, attrs, polarity, counts, measures

    if len(verbs) >= 2:  # coordinated clauses: «открой файл и сохрани документ»
        subj_nouns = [(ni, c) for ni, c in nouns if ni < verbs[0][0]]
        subject = subj_nouns[-1][1] if subj_nouns else "concept.you"  # shared subject
        triples = []
        for idx, (vp, rel) in enumerate(verbs):
            nxt = verbs[idx + 1][0] if idx + 1 < len(verbs) else len(seq)
            objs = [(ni, c) for ni, c in nouns if vp < ni < nxt]
            if objs:
                triples.append((rel, subject, head(objs)))
        return triples, attrs, polarity, counts, measures

    if verbs and nouns:  # single verb — imperative (no subject) or transitive S-V-O
        verb_pos = verbs[0][0]
        before = [(ni, c) for ni, c in nouns if ni < verb_pos]
        after = [(ni, c) for ni, c in nouns if ni > verb_pos]
        subject = before[-1][1] if before else "concept.you"  # implicit «you» for imperative
        if after:
            # «удали файл и папку» — coordinated objects (one edge each); else compound head
            objs = [c for _, c in after] if (has_and and len(after) >= 2) else [head(after)]
            return [(verbs[0][1], subject, o) for o in objs], attrs, polarity, counts, measures

    # predicative state: «файл открыт» / «the file is open» → has_state(file, concept.open) —
    # a state predicate after a noun, no relation of its own (the building block of a rule)
    if nouns and not preps and not verbs and any(k == "state" for k, _ in seq):
        state_triples = []
        for ci, (k, p) in enumerate(seq):
            if k == "state":
                figs = [c for ni, c in nouns if ni < ci]
                if figs:
                    state_triples.append(("has_state", figs[-1], f"concept.{p}"))
        if state_triples:
            return state_triples, attrs, polarity, counts, measures

    # predicative colour: «яблоко красное» → color_of(apple, concept.red) — a colour adjective
    # AFTER a noun, with no relation of its own
    if nouns and not preps and not verbs:
        color_triples = []
        for ci, (k, p) in enumerate(seq):
            if k == "adj" and p in COLOR_IDS:
                figs = [c for ni, c in nouns if ni < ci]
                if figs:
                    color_triples.append(("color_of", figs[-1], f"concept.{p}"))
        if color_triples:
            return color_triples, attrs, polarity, counts, measures
    return [], attrs, polarity, counts, measures


def parse_triples(state: dict, lattice_id: str, text: str) -> list[tuple[str, str, str]]:
    """Parse a controlled clause into (relation, concept, concept) triples (concept ids)."""
    return parse_situation(state, lattice_id, text)[0]


def parse_graph(state: dict, lattice_id: str, text: str) -> dict[str, Any]:
    """Parse text and build its meaning graph: adjective attributes, counts and measures on
    the nodes, clause polarity on the edges (a negated clause marks ``polarity='neg'``)."""
    triples, attrs, polarity, counts, measures = parse_situation(state, lattice_id, text)
    graph = meaning_graph(state, lattice_id, triples)
    for cid, aids in attrs.items():
        if cid in graph["nodes"]:
            graph["nodes"][cid]["attrs"] = aids
    for cid, n in counts.items():
        if cid in graph["nodes"]:
            graph["nodes"][cid]["count"] = n
    for cid, m in measures.items():
        if cid in graph["nodes"]:
            graph["nodes"][cid]["measure"] = m
    for edge in graph["edges"]:
        edge["polarity"] = polarity
    return graph


def parse_fingerprint(state: dict, lattice_id: str, text: str) -> dict[str, Any]:
    """Parse text all the way to its situation fingerprint."""
    return fingerprint(parse_graph(state, lattice_id, text))


def _clause_parses(state: dict, lattice_id: str, text: str) -> bool:
    return any(e.get("satisfied") for e in parse_graph(state, lattice_id, text).get("edges", []))


def split_conditions(state: dict, lattice_id: str, text: str) -> list[str]:
    """Split one rule side into independently-parsing condition clauses. Splits on a
    separator («,» «;» «и» «and») ONLY when every fragment parses on its own — so a
    conjunction of clauses («файл открыт и яблоко на столе») becomes two conditions, while
    intra-clause coordination («яблоко и книга на столе», where «яблоко» alone is no clause)
    is left whole for the clause parser. This is what lets «если X и Y, то Z» mix forms
    (a state AND a locative) that a single clause parse cannot express together."""
    text = text.strip(" ,;\t")
    for sep in (r"\s*[,;]\s*", r"\s+и\s+", r"\s+and\s+"):
        parts = [p.strip() for p in re.split(sep, text, flags=re.IGNORECASE) if p.strip()]
        if len(parts) > 1 and all(_clause_parses(state, lattice_id, p) for p in parts):
            return [c for p in parts for c in split_conditions(state, lattice_id, p)]
    return [text]


def _merge_graphs(graphs: list[dict[str, Any]]) -> dict[str, Any]:
    """Union several meaning graphs into one — the conjunction of conditions (nodes merged,
    satisfied edges concatenated, deduplicated by (rel, src, dst, polarity))."""
    nodes: dict[str, Any] = {}
    edges: list[dict[str, Any]] = []
    seen: set[tuple] = set()
    for g in graphs:
        nodes.update(g.get("nodes", {}))
        for e in g.get("edges", []):
            key = (e.get("rel"), e.get("src"), e.get("dst"), e.get("polarity", "pos"))
            if key not in seen:
                seen.add(key)
                edges.append(e)
    return {"nodes": nodes, "edges": edges, "valid": all(e.get("satisfied") for e in edges)}


def _parse_conjunction(state: dict, lattice_id: str, text: str) -> dict[str, Any]:
    """Parse a rule side (possibly «X и Y и …») into one merged graph of all its conditions."""
    return _merge_graphs([parse_graph(state, lattice_id, c) for c in split_conditions(state, lattice_id, text)])


def parse_rule(state: dict, lattice_id: str, text: str) -> dict[str, Any] | None:
    """Parse a conditional «если X, то Y» / «if X then Y» into a RULE — an antecedent graph
    and a consequent graph. Each side may be a CONJUNCTION of conditions («если X и Y, то Z»):
    it is split into independently-parsing clauses (so it can mix forms — a state AND a
    locative) and unioned. Returns ``None`` if the text is not a conditional or a side does
    not parse to any situation. The building block reasoning checks facts against."""
    t = str(text or "").strip()
    m = re.match(r"(?is)^\s*(?:если|if)\b\s*(.+)$", t)
    if not m:
        return None
    rest = m.group(1)
    parts = re.split(r"(?i)(?:,\s*)?\b(?:то|then)\b", rest, maxsplit=1)
    if len(parts) == 2:
        ante, cons = parts
    elif "," in rest:  # «если X, Y» — comma separates when «то/then» is dropped
        ante, cons = rest.split(",", 1)
    else:
        return None
    ante, cons = ante.strip(" ,\t"), cons.strip(" ,\t")
    if not ante or not cons:
        return None
    ga, gc = _parse_conjunction(state, lattice_id, ante), _parse_conjunction(state, lattice_id, cons)
    if not any(e.get("satisfied") for e in ga["edges"]) or not any(e.get("satisfied") for e in gc["edges"]):
        return None  # a side did not parse — honest, like the validator's «uncheckable»
    return {"text": t, "antecedent_text": ante, "consequent_text": cons,
            "antecedent": ga, "consequent": gc,
            "antecedent_conditions": split_conditions(state, lattice_id, ante),
            "consequent_conditions": split_conditions(state, lattice_id, cons)}
