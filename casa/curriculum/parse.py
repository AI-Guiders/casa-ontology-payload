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
from casa.curriculum.situation import PREDICATE_RELATION, PREDICATE_RELATION_ES, fingerprint, normalize_relation

_PREPS = {"на", "в", "у", "около", "рядом", "под", "над", "on", "in", "near", "by", "under", "inside", "beside",
          "to", "into"}  # «to/into» — action destination
_POSITIONAL = {"лежит", "стоит", "находится", "лежать", "стоять", "находиться", "висит",
               "lies", "stands", "sits", "is", "hangs",
               "сделан", "сделана", "сделано", "сделаны", "made",  # made_of copula
               "than", "чем"}  # comparison connector («bigger than», «больше, чем»)
_NEG = {"не", "нет", "ни", "not", "don't", "do not", "doesn't", "no", "never"}  # negation markers
_AND = {"и", "and", "y", "e"}  # coordinator — distributes a role over conjuncts («y/e» — Spanish, no collisions)
_COPULA = {"is", "are", "está", "están", "son"}  # predicative copula (EN + safe ES forms) — marks the next word as a state predicate

# --- Spanish layer (activated ONLY by lang="es"): Spanish shares the Latin script with
# English, so these cannot be merged into the shared sets — ES preposition «a» is the EN
# article, ES «sin» (without) is the EN «sin»; surfaces that DON'T collide (y/está/nunca)
# are merged above. Verbs/prepositions map to relations via PREDICATE_RELATION_ES.
# NB: «de» is NOT a preposition here — it mirrors EN «of» (a made_of VERB via the predicate
# table), so «5 ml de agua en la mesa» keeps the locative as its only prepositional edge.
_PREPS_ES = {"en", "sobre", "encima", "dentro", "cerca", "junto", "a"}
# clause-level negation only: «sin» is NOT here — «sin abrir» (unopened) is a participle
# modifier, and marking it negative once masked a dropped «no» (a false «equivalent»)
_NEG_ES = {"nunca", "jamás", "jamas"}
_POSITIONAL_ES = {"hecho", "hecha", "hechos", "hechas", "que"}  # made-of copula; «más grande que»
_CMP_ES = {"más": "gt", "mayor": "gt", "supera": "gt", "excede": "gt",
           "menos": "lt", "menor": "lt", "igual": "eq"}
# ES homographs of EN surfaces — words a Spanish clause must NOT read the English way:
# blocked from adjective/colour classification and from name resolution (ES «red» is a
# network, not the colour). Value = the concept to resolve to, or None = honest refusal.
_ES_HOMOGRAPHS: dict[str, str | None] = {"red": None}
# numeric comparison operators (surface -> base op). «больше»+noun stays object-comparison
# (bigger_than); «больше»+number becomes a numeric threshold (num_gt). «than»/«чем» are skipped
# as positional connectors. Mapped to num_gt/num_lt/num_eq edges to a concept.amount node.
_CMP = {
    "больше": "gt", "более": "gt", "bigger": "gt", "greater": "gt", "more": "gt", "превышает": "gt", "exceeds": "gt",
    "меньше": "lt", "менее": "lt", "less": "lt", "fewer": "lt", "smaller": "lt",
    "равно": "eq", "равна": "eq", "равен": "eq", "равны": "eq", "equals": "eq", "equal": "eq",
}
_CMP_REL = {"gt": "num_gt", "lt": "num_lt", "eq": "num_eq"}
AMOUNT = "concept.amount"  # synthetic node carrying the threshold's {value, unit} measure


def _tokens(text: str) -> list[str]:
    # decimals stay ONE token («9,75 mg» must not become 9 and 75 — a dose-kernel hazard)
    return re.findall(r"\d+[.,]\d+|[\wЀ-ӿ]+", str(text or "").lower(), flags=re.UNICODE)


# temporal/frequency nouns are NOT modelled (no time in the graph) and must never capture a
# measure: in «15 mg once a day» the amount belongs to the dose, not to the day. Skipped in
# token classification like any unknown word — honest scope, not silent misbinding.
_TEMPORAL_SKIP = {
    "day", "days", "week", "weeks", "month", "months", "year", "years", "hour", "hours",
    "día", "dia", "días", "dias", "semana", "semanas", "mes", "meses", "año", "años",
    "hora", "horas", "vez", "veces",
    "день", "дня", "дней", "неделя", "недели", "недель", "месяц", "месяца", "месяцев",
    "год", "года", "лет", "час", "часа", "часов", "раз", "раза",
}

# glued number+unit («2ml», «10мг») — split into the pair the classifier expects
_GLUED_MEASURE = re.compile(r"^(\d+(?:[.,]\d+)?)([a-zа-яµ]+)$")

_CAPWORD = re.compile(r"[A-ZÁÉÍÓÚÑ][\wÁ-ÿ]*")


def _named_candidates(text: str) -> set[str]:
    """Lowercased surfaces that look like PROPER NAMES in the original casing: capitalized
    mid-sentence, or ALL-CAPS anywhere (≥3 letters). «Mid-sentence» demands a letter/digit
    right before the token: sentence-initial TitleCase — including after a list bullet
    («- Tome…», «2 - Abra…») — does not qualify, it is ordinary sentence capitalization
    (mirrored by the benchmark's entity injector, benchmark._find_drug_name)."""
    out: set[str] = set()
    for m in _CAPWORD.finditer(str(text or "")):
        tok = m.group(0)
        if len(tok) >= 3 and tok.isupper():
            out.add(tok.lower())
            continue
        head = text[:m.start()].rstrip()
        if head and head[-1].isalnum():
            out.add(tok.lower())
    return out


def _normalize_name(surface: str) -> str:
    """Cross-lingual normalization of a proper name (INN drug names vary by a final vowel
    and consonant doubling: aripiprazole/aripiprazol, amoxicillin/amoxicilina). Lowercase,
    collapse doubled letters, strip ONE trailing a/e/o on long names. Heuristic — entity
    verdicts compare NORMALIZED names, stated honestly in the validator's scope."""
    s = surface.strip().lower()
    s = re.sub(r"(.)\1", r"\1", s)  # collapse doubles (amoxicillin -> amoxicilin)
    if len(s) > 4 and s[-1] in "aeo":
        s = s[:-1]
    return s


def _typed_concepts(state: dict, lattice_id: str) -> set[str]:
    """Concepts that are IN the ontology (appear as the source of an isa edge)."""
    from casa.curriculum.concept_net import decoded_edges
    from casa.prisms.memory.memory_prisms import memory_lattices

    lat = memory_lattices(state).get(lattice_id)
    edges = decoded_edges(lat) if lat else []
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


def resolve_token(state: dict, lattice_id: str, token: str, names: list[tuple[str, str]] | None = None,
                  lang: str | None = None) -> str | None:
    """Resolve a (possibly inflected) word to a concept: exact name, English/Spanish plural
    lemma, then Russian stem match.

    ``lang="es"`` applies the homograph guard first — a shared Latin spelling must not
    resolve to the ENGLISH concept (ES «red» is a network, not the colour).

    Russian lemma match picks the surface that is the token's base form: the longest common
    prefix wins, then the shortest surface — so «столе» resolves to «стол» (lemma,
    differs by an ending), not «столб» (a different, longer word)."""
    from casa.curriculum.translate import script_of

    if lang == "es":
        if token in _ES_HOMOGRAPHS:
            return _ES_HOMOGRAPHS[token]  # mapped concept, or None = honest refusal
        # Spanish resolves ONLY through its tagged names (lang.word.es.*) — untagged Latin
        # names are English and must not leak into a declared-Spanish clause
        c = concept_of(state, lattice_id, token, lang="es")
        if c:
            return c
        for cand in _en_singulars(token):  # -s/-es plural strip works for Spanish too
            c = concept_of(state, lattice_id, cand, lang="es")
            if c:
                return c
        return None
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
    state: dict, lattice_id: str, text: str, lang: str | None = None
) -> tuple[list[tuple[str, str, str]], dict[str, list[str]], str, dict[str, int], dict[str, dict]]:
    """Parse a controlled clause into triples, attributes, polarity, counts, and measures.

    Returns ``(triples, attrs, polarity, counts, measures)``: ``attrs[cid]`` are attribute
    ids («red»), ``counts[cid]`` a plain count («два файла» → 2), and ``measures[cid]`` a
    measure with a unit («5 мл воды» → {value:5, unit:'ml'}) — all bind to the next noun;
    ``polarity`` is ``"neg"`` for a negated clause, else ``"pos"``.

    ``lang`` declares the clause language when the script can't («es» — Spanish shares the
    Latin script with English): it activates the Spanish function-word/predicate layer and
    the homograph guard. ``None`` keeps the RU/EN behaviour exactly."""
    from casa.curriculum.attributes import COLOR_IDS, attr_of_token
    from casa.curriculum.quantity import number_of_token, unit_of_token
    from casa.curriculum.states import state_of_token

    es = lang == "es"
    preps = _PREPS | _PREPS_ES if es else _PREPS
    neg = _NEG | _NEG_ES if es else _NEG
    positional = _POSITIONAL | _POSITIONAL_ES if es else _POSITIONAL
    cmp_ops = {**_CMP, **_CMP_ES} if es else _CMP
    is_verb = (lambda t: t in PREDICATE_RELATION or t in PREDICATE_RELATION_ES) if es \
        else (lambda t: t in PREDICATE_RELATION)

    names = _name_index(state, lattice_id)
    # drug/proper names are an open class: on DECLARED-language sides (the benchmark knows
    # each side's language) an unknown capitalized token becomes an opaque named node —
    # so «no tome ABILIFY» parses AND a swapped drug is an entity-class divergence
    named = _named_candidates(text) if lang in ("en", "es") else set()
    seq: list[tuple[str, Any]] = []  # ('prep'|'verb'|'noun'|'adj'|'num'|'unit'|'state', payload)
    polarity = "pos"
    copula = False  # saw a copula («is/are», «está/son») — the next state word is predicative
    for tok in _tokens(text):
        if tok in _TEMPORAL_SKIP:
            # time/frequency is out of scope — must not capture measures; a number that
            # quantifies the temporal noun leaves with it («once a day», «una vez», «2 veces»
            # — otherwise «150 mg una vez al día» would overwrite the dose with 1)
            if seq and seq[-1][0] == "num":
                seq.pop()
            continue
        if (gm := _GLUED_MEASURE.match(tok)) and unit_of_token(gm.group(2)) is not None:
            seq.append(("num", number_of_token(gm.group(1))))
            seq.append(("unit", unit_of_token(gm.group(2))))
            continue
        if tok in neg:
            polarity = "neg"  # negation marker — scopes the clause's relation
        elif tok in _AND:
            seq.append(("and", None))  # coordinator
        elif tok in _COPULA:
            copula = True  # «the file is open» — marks the following state predicate
        elif es and tok == "en":
            seq.append(("prep", "__es_en__"))  # ES «en» covers BOTH on/in — resolved by the
            # ground's affordances below (mesa → on, carpeta → in); the ontology disambiguates
        elif tok in preps:
            seq.append(("prep", normalize_relation(tok, lang)))
        elif tok in positional:
            continue  # positional copula — the preposition carries the relation
        elif (sid := state_of_token(tok)) is not None and (copula or not is_verb(tok)):
            seq.append(("state", sid))  # predicative state; an EN verb/adj clash («open») needs the copula
        elif tok in cmp_ops:
            seq.append(("cmp", cmp_ops[tok]))  # numeric/object comparison operator
        elif is_verb(tok) and tok not in preps:
            seq.append(("verb", normalize_relation(tok, lang)))
        elif (num := number_of_token(tok)) is not None:
            seq.append(("num", num))
        elif (unit := unit_of_token(tok)) is not None:
            seq.append(("unit", unit))
        elif (aid := attr_of_token(tok)) is not None and not (es and tok in _ES_HOMOGRAPHS):
            seq.append(("adj", aid))  # ES homographs of EN adjectives never classify as attrs
        else:
            cid = resolve_token(state, lattice_id, tok, names, lang=lang)
            if cid:
                seq.append(("noun", cid))
                continue
            # unknown word: a proper name (capitalized/ALL-CAPS), or the substance right
            # after «measure + of/de» («9,75 mg de aripiprazol» — INN generics are
            # lowercase, the partitive position identifies them)
            after_measure_of = (lang in ("en", "es") and len(seq) >= 2
                                and seq[-1] == ("verb", "made_of") and seq[-2][0] == "unit")
            if tok in named or after_measure_of:
                from casa.curriculum.concept_net import NAMED_PREFIX

                seq.append(("noun", f"{NAMED_PREFIX}{_normalize_name(tok)}"))

    if es:  # resolve the underspecified ES «en» per ground: a support surface hosts ON, else IN
        from casa.curriculum.concept_net import affordances_of

        for i, (k, p) in enumerate(seq):
            if k == "prep" and p == "__es_en__":
                ground = next((c for kk, c in seq[i + 1:] if kk == "noun"), None)
                aff = affordances_of(state, lattice_id, ground) if ground else set()
                seq[i] = ("prep", "on" if "support_surface" in aff else "in")

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

    # partitive/dangling «of/de» is NOT a made_of claim: before a number ("a dose of
    # 75 mg"), before a NAMED substance ("9,75 mg de aripiprazol" — the measure must bind
    # to the substance, not spawn a made_of edge), or with no noun following it at all —
    # drop the spurious verb so the measure forms below see through
    from casa.curriculum.concept_net import NAMED_PREFIX as _NP

    seq = [item for i, item in enumerate(seq)
           if not (item[0] == "verb" and item[1] == "made_of"
                   and (i + 1 >= len(seq) or seq[i + 1][0] == "num"
                        or (seq[i + 1][0] == "noun" and str(seq[i + 1][1]).startswith(_NP))
                        or not any(k == "noun" for k, _ in seq[i + 1:])))]

    nouns = [(i, p) for i, (k, p) in enumerate(seq) if k == "noun"]
    preps = [(i, p) for i, (k, p) in enumerate(seq) if k == "prep"]
    verbs = [(i, p) for i, (k, p) in enumerate(seq) if k == "verb"]
    has_and = any(k == "and" for k, _ in seq)
    # the head of a noun-noun compound differs by language: English head-LAST («icon file» →
    # file), Russian genitive head-FIRST («файл пиктограммы» → файл).
    is_ru = bool(re.search(r"[Ѐ-ӿ]", text))
    head = lambda ns: ns[0][1] if is_ru else ns[-1][1]  # noqa: E731

    # comparison: «доза больше 5 мл» (numeric threshold) or «слон больше мыши» (objects).
    # A number after the operator → a num_gt/num_lt/num_eq edge to the AMOUNT node carrying
    # the threshold's {value, unit}; a noun after «больше» → the object bigger_than relation.
    cmps = [i for i, (k, _) in enumerate(seq) if k == "cmp"]
    if cmps:
        ci = cmps[0]
        op = next(p for k, p in seq if k == "cmp")
        before_n = [c for ni, c in nouns if ni < ci]
        after_n = [c for ni, c in nouns if ni > ci]
        nums = [p for k, p in seq[ci + 1:] if k == "num"]
        units = [p for k, p in seq[ci + 1:] if k == "unit"]
        if before_n and nums:  # numeric threshold
            measures[AMOUNT] = {"value": nums[0], "unit": units[0] if units else ""}
            return [(_CMP_REL[op], before_n[-1], AMOUNT)], attrs, polarity, counts, measures
        if op == "gt" and before_n and after_n:  # object comparison «слон больше мыши»
            return [("bigger_than", before_n[-1], after_n[0])], attrs, polarity, counts, measures

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
        # the destination is the compound head of the noun run after the preposition
        # («in the original package» → package, not the modifier that happens to resolve)
        nxt_pp = next((qi for qi, _ in preps if qi > pp), len(seq))
        dest_run = [(ni, c) for ni, c in nouns if pp < ni < nxt_pp]
        # elliptic label imperative: «Conservar en nevera» / «Store in a refrigerator» —
        # the storage verb with NO object names the labelled product itself; both sides
        # of a pair get the SAME implicit node, so the forms stay comparable. Only the
        # store verb: other verb+prep clauses («click on the button») keep their parse.
        if not obj_nouns and not subj_nouns and dest_run and vrel == "store" and lang in ("en", "es"):
            obj = "concept.medicine"
            return [(vrel, subject, obj), (prel, obj, head(dest_run))], attrs, polarity, counts, measures
        if obj_nouns and dest_run:
            obj = head(obj_nouns)
            return [(vrel, subject, obj), (prel, obj, head(dest_run))], attrs, polarity, counts, measures

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
            # the ground is the compound head of the noun run up to the next preposition
            # («in the original package» → package). Only when the figure stands BEFORE
            # the preposition: in the inverted form («на столе яблоко») the run after the
            # preposition is ground THEN figure, not a compound.
            nxt_pi = next((qi for qi, _ in preps if qi > pi), len(seq))
            run = [(ni, c) for ni, c in nouns if pi < ni < nxt_pi]
            ground = head(run) if run and before else after[0]
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
        if triples:  # no objects matched — not coordination; fall through (measure claims etc.)
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

    # measure claim: «доза — 75 мг» / "the dose is 75 mg" / «el vial contiene 3 ml» — a
    # trailing number+unit with no following noun to bind to IS the claim itself: the
    # figure equals that amount (num_eq into the value-mutex/threshold machinery). The
    # label corpus's most frequent checkable form.
    if pending_unit is not None and nouns and not preps:
        last_meas = max(i for i, (k, _p) in enumerate(seq) if k in ("num", "unit"))
        figs = [c for ni, c in nouns if ni < last_meas]
        if figs:
            measures[AMOUNT] = {"value": pending_count or 1, "unit": pending_unit}
            return [("num_eq", figs[-1], AMOUNT)], attrs, polarity, counts, measures

    return [], attrs, polarity, counts, measures


def parse_triples(state: dict, lattice_id: str, text: str, lang: str | None = None) -> list[tuple[str, str, str]]:
    """Parse a controlled clause into (relation, concept, concept) triples (concept ids)."""
    return parse_situation(state, lattice_id, text, lang=lang)[0]


def parse_graph(state: dict, lattice_id: str, text: str, lang: str | None = None) -> dict[str, Any]:
    """Parse text and build its meaning graph: adjective attributes, counts and measures on
    the nodes, clause polarity on the edges (a negated clause marks ``polarity='neg'``)."""
    triples, attrs, polarity, counts, measures = parse_situation(state, lattice_id, text, lang=lang)
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


def parse_fingerprint(state: dict, lattice_id: str, text: str, lang: str | None = None) -> dict[str, Any]:
    """Parse text all the way to its situation fingerprint."""
    return fingerprint(parse_graph(state, lattice_id, text, lang=lang))


def _clause_parses(state: dict, lattice_id: str, text: str, lang: str | None = None) -> bool:
    return any(e.get("satisfied") for e in parse_graph(state, lattice_id, text, lang=lang).get("edges", []))


def split_conditions(state: dict, lattice_id: str, text: str, lang: str | None = None) -> list[str]:
    """Split one rule side into independently-parsing condition clauses. Splits on a
    separator («,» «;» «и» «and») ONLY when every fragment parses on its own — so a
    conjunction of clauses («файл открыт и яблоко на столе») becomes two conditions, while
    intra-clause coordination («яблоко и книга на столе», where «яблоко» alone is no clause)
    is left whole for the clause parser. This is what lets «если X и Y, то Z» mix forms
    (a state AND a locative) that a single clause parse cannot express together."""
    text = text.strip(" ,;\t")
    for sep in (r"\s*[,;]\s*", r"\s+и\s+", r"\s+and\s+", r"\s+y\s+"):
        parts = [p.strip() for p in re.split(sep, text, flags=re.IGNORECASE) if p.strip()]
        if len(parts) > 1 and all(_clause_parses(state, lattice_id, p, lang=lang) for p in parts):
            return [c for p in parts for c in split_conditions(state, lattice_id, p, lang=lang)]
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


def _parse_conjunction(state: dict, lattice_id: str, text: str, lang: str | None = None) -> dict[str, Any]:
    """Parse a rule side (possibly «X и Y и …») into one merged graph of all its conditions."""
    return _merge_graphs([parse_graph(state, lattice_id, c, lang=lang)
                          for c in split_conditions(state, lattice_id, text, lang=lang)])


def parse_rule(state: dict, lattice_id: str, text: str, lang: str | None = None) -> dict[str, Any] | None:
    """Parse a conditional «если X, то Y» / «if X then Y» into a RULE — an antecedent graph
    and a consequent graph. Each side may be a CONJUNCTION of conditions («если X и Y, то Z»):
    it is split into independently-parsing clauses (so it can mix forms — a state AND a
    locative) and unioned. Returns ``None`` if the text is not a conditional or a side does
    not parse to any situation. The building block reasoning checks facts against."""
    t = str(text or "").strip()
    m = re.match(r"(?is)^\s*(?:если|if|si)\b\s*(.+)$", t)
    if not m:
        return None
    rest = m.group(1)
    parts = re.split(r"(?i)(?:,\s*)?\b(?:то|then|entonces)\b", rest, maxsplit=1)
    if len(parts) == 2:
        ante, cons = parts
    elif "," in rest:  # «если X, Y» — comma separates when «то/then» is dropped
        ante, cons = rest.split(",", 1)
    else:
        return None
    ante, cons = ante.strip(" ,\t"), cons.strip(" ,\t")
    if not ante or not cons:
        return None
    ga = _parse_conjunction(state, lattice_id, ante, lang=lang)
    gc = _parse_conjunction(state, lattice_id, cons, lang=lang)
    if not any(e.get("satisfied") for e in ga["edges"]) or not any(e.get("satisfied") for e in gc["edges"]):
        return None  # a side did not parse — honest, like the validator's «uncheckable»
    return {"text": t, "antecedent_text": ante, "consequent_text": cons,
            "antecedent": ga, "consequent": gc,
            "antecedent_conditions": split_conditions(state, lattice_id, ante, lang=lang),
            "consequent_conditions": split_conditions(state, lattice_id, cons, lang=lang)}
