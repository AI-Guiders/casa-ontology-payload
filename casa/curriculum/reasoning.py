#!/usr/bin/env python3
"""Reasoning over situations — deterministic consistency checking on the concept graph.

The equivalence validator asks «do two sentences SAY the same thing?» (translation QA).
This module asks the *logic* question «can two statements BE true together?» — the same
language-independent fingerprint, pointed at consistency instead of equivalence. It is the
deterministic guardrail generalised from one translation pair to a SET of assertions: feed
N statements, get back the contradictions and entailments as an auditable graph relation —
the thing a probabilistic LLM cannot guarantee.

The relation between two situations A and B (both must parse, else «unknown» — honest):
  equivalent   — identical satisfied-edge sets (the same situation).
  entails      — A's edges ⊋ B's: A is the more specific situation, so A ⊨ B
                 («яблоко на столе у окна» ⊨ «яблоко на столе»).
  entailed_by  — B ⊨ A (the other direction).
  contradicts  — a shared fact cannot hold both ways: opposite polarity, different count,
                 different unit/measure, or a conflicting value of a FUNCTIONAL relation
                 (one colour per thing). These are exactly the dangerous classes the kernel
                 already adjudicates cross-lingually — here within one language, across claims.
  independent  — none of the above (disjoint, or overlapping without entailment).

Honest scope: entailment is EXACT edge-set containment — attribute specialisation
(«красное яблоко» ⊨ «яблоко») is deliberately NOT claimed (the attribute is in the edge
key), so the tool never over-asserts. Contradiction covers the polarity/quantity/unit
kernel plus relations declared functional, not world knowledge: «на столе» vs «на полке»
is independent here, because location is not modelled as one-valued.
"""

from __future__ import annotations

import re
from typing import Any

# relations mapping a subject to exactly ONE value — a differing value is a contradiction.
# Kept deliberately minimal: colour is genuinely one-per-thing; size/location are not.
_FUNCTIONAL = {"color_of"}

# numeric threshold relations (parse.py): num_gt/num_lt/num_eq(subject, amount{value,unit})
_NUM_OP = {"num_gt": "gt", "num_lt": "lt", "num_eq": "eq"}
_OP_SYM = {"gt": ">", "lt": "<", "eq": "="}
# parse a canonical numeric edge «num_gt(concept.dose,concept.amount{15ml})» -> op/value/unit
_NUM_CANON = re.compile(r"^(num_gt|num_lt|num_eq)\((.+),concept\.amount\{(\d+(?:\.\d+)?)(\D*)\}\)$")


def _constraint_entails(fo: str, fv: float, ao: str, av: float) -> bool:
    """Does a FACT constraint (fo fv) entail an ANTECEDENT constraint (ao av) — i.e. does
    every x satisfying the fact also satisfy the antecedent? «=15» entails «>10» (15>10);
    «>12» entails «>10» (x>12 ⊆ x>10). This is how a value satisfies a threshold antecedent."""
    if ao == "eq":
        return fo == "eq" and fv == av
    if ao == "gt":
        return (fo == "eq" and fv > av) or (fo == "gt" and fv >= av)
    if ao == "lt":
        return (fo == "eq" and fv < av) or (fo == "lt" and fv <= av)
    return False


def _antecedent_support(ante_canon: set[str], fact_canon: set[str]) -> set[str] | None:
    """Is the antecedent established by the facts? Returns the set of supporting FACT edges
    (for provenance), or ``None`` if not established. Non-numeric edges need exact membership;
    a numeric threshold edge is met by any fact constraint on the same subject that entails it
    (so «доза равна 15 мл» satisfies the antecedent «доза больше 10 мл»)."""
    fact_num: dict[str, list[tuple]] = {}
    for c in fact_canon:
        m = _NUM_CANON.match(c)
        if m:
            fact_num.setdefault(m.group(2), []).append((c, _NUM_OP[m.group(1)], float(m.group(3)), m.group(4)))
    support: set[str] = set()
    for a in ante_canon:
        m = _NUM_CANON.match(a)
        if m is None:  # ordinary edge — exact containment
            if a not in fact_canon:
                return None
            support.add(a)
            continue
        src, ao, av, au = m.group(2), _NUM_OP[m.group(1)], float(m.group(3)), m.group(4)
        hit = next((fc for fc, fo, fv, fu in fact_num.get(src, [])
                    if (not (fu and au) or fu == au) and _constraint_entails(fo, fv, ao, av)), None)
        if hit is None:
            return None
        support.add(hit)
    return support


def _ranges_conflict(o1: str, v1: float, o2: str, v2: float) -> bool:
    """Do two numeric constraints on the same quantity have an empty intersection?
    gt v ≡ x>v, lt v ≡ x<v, eq v ≡ x==v. e.g. «>10» ∧ «<5» is empty; «>5» ∧ «=3» is empty."""
    ops = {o1, o2}
    if o1 == "eq" and o2 == "eq":
        return v1 != v2
    if "eq" in ops:
        ev = v1 if o1 == "eq" else v2
        oo, ov = (o2, v2) if o1 == "eq" else (o1, v1)
        return ev <= ov if oo == "gt" else ev >= ov  # the eq value must satisfy the inequality
    if ops == {"gt", "lt"}:
        gv = v1 if o1 == "gt" else v2
        lv = v1 if o1 == "lt" else v2
        return gv >= lv  # (gv, ∞) ∩ (−∞, lv) is empty iff gv ≥ lv
    return False  # gt/gt or lt/lt are always jointly satisfiable


def _contradictions(a_edges: list[dict], b_edges: list[dict]) -> list[dict[str, str]]:
    """Edge-level conflicts that stop A and B from holding together (the logic kernel).
    Reuses the equivalence validator's dangerous classes (polarity / quantity / unit), but
    NOT its «structure»/«attribute» divergences — an extra or more-specific edge is not a
    contradiction, only a differing value on the SAME fact is."""
    def skel(e: dict) -> tuple[str, str, str]:
        return (e["rel"], e["src"], e["dst"])

    by_a = {skel(e): e for e in a_edges}
    by_b = {skel(e): e for e in b_edges}
    out: list[dict[str, str]] = []

    for k in by_a.keys() & by_b.keys():  # same (rel, src, dst) — do the modifiers conflict?
        s, t, rel = by_a[k], by_b[k], k[0]
        if s["polarity"] != t["polarity"]:
            out.append({"class": "polarity", "note": f"«{rel}»: одно утверждает, другое отрицает"})
        if rel in _NUM_OP:
            continue  # numeric thresholds: the interval logic below owns value/unit conflicts
        if s["src_count"] != t["src_count"] or s["d_count"] != t["d_count"]:
            sc = s["d_count"] if s["src_count"] == t["src_count"] else s["src_count"]
            tc = t["d_count"] if s["src_count"] == t["src_count"] else t["src_count"]
            out.append({"class": "quantity", "note": f"«{rel}»: количество {sc} vs {tc}"})
        sm, tm = (s["src_meas"] or s["d_meas"]), (t["src_meas"] or t["d_meas"])
        if sm != tm and sm and tm:
            if sm[1] != tm[1]:
                out.append({"class": "unit", "note": f"«{rel}»: единица {sm[1]} vs {tm[1]}"})
            else:
                out.append({"class": "quantity", "note": f"«{rel}»: мера {sm[0]}{sm[1]} vs {tm[0]}{tm[1]}"})

    # functional relations: same (rel, subject), a different value -> conflict (one colour)
    for rel in _FUNCTIONAL:
        a_vals: dict[str, set[str]] = {}
        for e in a_edges:
            if e["rel"] == rel and e["polarity"] == "pos":
                a_vals.setdefault(e["src"], set()).add(e["dst"])
        for e in b_edges:
            if e["rel"] == rel and e["polarity"] == "pos" and e["src"] in a_vals and e["dst"] not in a_vals[e["src"]]:
                other = sorted(a_vals[e["src"]])[0].split(".")[-1]
                out.append({"class": "functional",
                            "note": f"«{rel}»: {e['src'].split('.')[-1]} → {other} vs {e['dst'].split('.')[-1]}"})

    # mutually exclusive states: has_state(x, open) vs has_state(x, closed) -> contradiction
    from casa.curriculum.states import are_antonyms

    a_states: dict[str, set[str]] = {}
    for e in a_edges:
        if e["rel"] == "has_state" and e["polarity"] == "pos":
            a_states.setdefault(e["src"], set()).add(e["dst"].split(".")[-1])
    for e in b_edges:
        if e["rel"] == "has_state" and e["polarity"] == "pos":
            sb = e["dst"].split(".")[-1]
            for sa in a_states.get(e["src"], ()):
                if are_antonyms(sa, sb):
                    out.append({"class": "state",
                                "note": f"«{e['src'].split('.')[-1]}»: {sa} vs {sb} — взаимоисключающие"})

    # numeric value mutex: gt/lt/eq thresholds on the same quantity with a disjoint range
    def _consts(edges: list[dict]) -> dict[str, list[tuple]]:
        out_: dict[str, list[tuple]] = {}
        for e in edges:
            if e["rel"] in _NUM_OP and e["polarity"] == "pos" and e["d_meas"]:
                out_.setdefault(e["src"], []).append((_NUM_OP[e["rel"]], e["d_meas"][0], e["d_meas"][1]))
        return out_

    ac, bc = _consts(a_edges), _consts(b_edges)
    for subj in ac.keys() & bc.keys():
        name = subj.split(".")[-1]
        for o1, v1, u1 in ac[subj]:
            for o2, v2, u2 in bc[subj]:
                if u1 and u2 and u1 != u2:
                    out.append({"class": "unit", "note": f"«{name}»: единица {u1} vs {u2}"})
                elif _ranges_conflict(o1, v1, o2, v2):
                    out.append({"class": "range",
                                "note": f"«{name}»: {_OP_SYM[o1]}{v1}{u1} vs {_OP_SYM[o2]}{v2}{u2} — несовместимо"})
    return out


def relate(state: dict, lattice_id: str, a: str, b: str) -> dict[str, Any]:
    """Classify the logical relation between two statements. See the module docstring."""
    from casa.curriculum.equivalence import _structured_edges  # shared structured-edge extractor
    from casa.curriculum.parse import parse_graph
    from casa.curriculum.situation import canonical_edges

    ga, gb = parse_graph(state, lattice_id, a), parse_graph(state, lattice_id, b)
    ea, eb = _structured_edges(ga), _structured_edges(gb)
    res: dict[str, Any] = {
        "a": {"text": a, "parsed": bool(ea), "edges": canonical_edges(ga)},
        "b": {"text": b, "parsed": bool(eb), "edges": canonical_edges(gb)},
        "conflicts": [],
    }
    if not ea or not eb:
        res["verdict"] = "unknown"
        res["reason"] = "не разобрана хотя бы одна сторона — о связи судить нельзя"
        return res
    conflicts = _contradictions(ea, eb)
    if conflicts:
        res["verdict"] = "contradicts"
        res["conflicts"] = conflicts
        res["reason"] = "утверждения не могут быть истинны одновременно"
        return res
    sa, sb = set(res["a"]["edges"]), set(res["b"]["edges"])
    if sa == sb:
        res["verdict"], res["reason"] = "equivalent", "одна и та же ситуация"
    elif sa > sb:
        res["verdict"], res["reason"] = "entails", "A конкретнее — из A следует B"
    elif sb > sa:
        res["verdict"], res["reason"] = "entailed_by", "B конкретнее — из B следует A"
    else:
        res["verdict"], res["reason"] = "independent", "независимые ситуации"
    return res


def check_consistency(state: dict, lattice_id: str, statements: list[str]) -> dict[str, Any]:
    """Consistency of a SET of statements — the «feed N claims, get the contradictions»
    capability. Each statement is parsed ONCE, then every pair is scanned for a kernel
    contradiction. A statement that does not parse is reported as ``unparsed`` and excluded
    from judgement (never silently assumed consistent)."""
    from casa.curriculum.equivalence import _structured_edges
    from casa.curriculum.parse import parse_graph

    items: list[tuple[int, str, list[dict]]] = []
    unparsed: list[dict[str, Any]] = []
    for i, s in enumerate(statements):
        edges = _structured_edges(parse_graph(state, lattice_id, s))
        if edges:
            items.append((i, s, edges))
        else:
            unparsed.append({"index": i, "text": s})

    contradictions: list[dict[str, Any]] = []
    for x in range(len(items)):
        for y in range(x + 1, len(items)):
            conf = _contradictions(items[x][2], items[y][2])
            if conf:
                contradictions.append({
                    "a_index": items[x][0], "a": items[x][1],
                    "b_index": items[y][0], "b": items[y][1], "conflicts": conf,
                })
    return {
        "statements": len(statements),
        "checked": len(items),
        "unparsed": unparsed,
        "consistent": not contradictions,
        "contradictions": contradictions,
    }


def check_against_rules(state: dict, lattice_id: str, facts: list[str], rules: list[str]) -> dict[str, Any]:
    """Check a fact base against conditional RULES «если X, то Y» — the «rules + facts →
    violations» capability. For each rule whose antecedent the facts entail (X holds), the
    consequent Y must hold: if the facts CONTRADICT Y (the dangerous kernel / state mutex),
    that is a **violation** — an auditable «if the file is open the button must be active,
    but the button is inactive». A rule whose antecedent does not hold is ``inactive``; one
    whose consequent is present is ``satisfied``; present-neither is ``fired_unknown``
    (fired but the consequent is simply unstated). Honest: unparsed facts/rules are reported,
    not assumed."""
    from casa.curriculum.equivalence import _structured_edges
    from casa.curriculum.parse import parse_graph, parse_rule
    from casa.curriculum.situation import canonical_edges

    fact_edges: list[dict] = []
    fact_canon: set[str] = set()
    unparsed_facts: list[dict[str, Any]] = []
    for i, f in enumerate(facts):
        g = parse_graph(state, lattice_id, f)
        se = _structured_edges(g)
        if se:
            fact_edges += se
            fact_canon |= set(canonical_edges(g))
        else:
            unparsed_facts.append({"index": i, "text": f})

    results: list[dict[str, Any]] = []
    for j, r in enumerate(rules):
        rule = parse_rule(state, lattice_id, r)
        if rule is None:
            results.append({"index": j, "text": r, "status": "unparsed_rule"})
            continue
        ante_canon = set(canonical_edges(rule["antecedent"]))
        cons_canon = set(canonical_edges(rule["consequent"]))
        cons_struct = _structured_edges(rule["consequent"])
        entry = {"index": j, "text": r, "antecedent_text": rule["antecedent_text"],
                 "consequent_text": rule["consequent_text"], "conflicts": []}
        if _antecedent_support(ante_canon, fact_canon) is None:
            entry["status"] = "inactive"  # antecedent not established by the facts
        elif (conflicts := _contradictions(cons_struct, fact_edges)):
            entry["status"], entry["conflicts"] = "violated", conflicts
        elif cons_canon <= fact_canon:
            entry["status"] = "satisfied"
        else:
            entry["status"] = "fired_unknown"  # fired, consequent neither present nor denied
        results.append(entry)

    violations = [e for e in results if e["status"] == "violated"]
    return {
        "facts": len(facts), "rules": len(rules),
        "unparsed_facts": unparsed_facts,
        "results": results,
        "violations": violations,
        "consistent": not violations,
    }


def forward_chain(state: dict, lattice_id: str, facts: list[str], rules: list[str],
                  *, max_steps: int = 32) -> dict[str, Any]:
    """Forward-chaining inference — derive new facts from rules, then keep checking until a
    fixpoint. A rule whose antecedent the facts entail and whose consequent is CONSISTENT
    adds that consequent to the fact base; the enlarged base can then fire further rules.
    A consequent that CONTRADICTS the base is a **violation** — and because facts are
    derived transitively, this catches contradictions several steps ahead that the direct
    one-shot check (`check_against_rules`) cannot see: «A», «если A то B», «если B то C»,
    «не C» → C is derived and clashes with ¬C two hops in.

    Every derived fact carries its rule + step (the audit trail); a violation is flagged
    ``chained`` when it is NOT explainable by the given facts alone (it needed a derivation).
    Facts grow monotonically, so this terminates; ``max_steps`` is a backstop."""
    from casa.curriculum.equivalence import _structured_edges
    from casa.curriculum.parse import _merge_graphs, parse_graph, parse_rule
    from casa.curriculum.situation import canonical_edges

    fact_graph: dict[str, Any] = {"nodes": {}, "edges": []}
    unparsed_facts: list[dict[str, Any]] = []
    for i, f in enumerate(facts):
        g = parse_graph(state, lattice_id, f)
        if any(e.get("satisfied") for e in g["edges"]):
            fact_graph = _merge_graphs([fact_graph, g])
        else:
            unparsed_facts.append({"index": i, "text": f})

    given_canon = set(canonical_edges(fact_graph))
    given_struct = _structured_edges(fact_graph)

    parsed_rules: list[tuple[int, str, dict]] = []
    unparsed_rules: list[dict[str, Any]] = []
    for j, r in enumerate(rules):
        rule = parse_rule(state, lattice_id, r)
        if rule:
            parsed_rules.append((j, r, rule))
        else:
            unparsed_rules.append({"index": j, "text": r})

    origin: dict[str, str] = {e: "given" for e in given_canon}  # edge -> 'given' | rule text
    # derivation[edge] = how it was produced: which rule, at which step, from which support
    # facts (the antecedent edges that fired the rule) — the provenance for the proof tree.
    derivation: dict[str, dict[str, Any]] = {}
    derived: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []
    violated: set[int] = set()

    steps = 0
    changed = True
    while changed and steps < max_steps:
        changed, steps = False, steps + 1
        fact_canon = set(canonical_edges(fact_graph))
        fact_struct = _structured_edges(fact_graph)
        for j, rtext, rule in parsed_rules:
            ante_canon = set(canonical_edges(rule["antecedent"]))
            support_set = _antecedent_support(ante_canon, fact_canon)
            if support_set is None:
                continue
            cons_struct = _structured_edges(rule["consequent"])
            cons_canon = set(canonical_edges(rule["consequent"]))
            support = sorted(support_set)  # the actual facts that make this rule applicable
            if (conflicts := _contradictions(cons_struct, fact_struct)):
                if j not in violated:
                    # direct iff the given facts alone establish the antecedent AND deny the consequent
                    direct = (_antecedent_support(ante_canon, given_canon) is not None
                              and bool(_contradictions(cons_struct, given_struct)))
                    violations.append({"rule_index": j, "rule": rtext, "conflicts": conflicts,
                                       "antecedent_text": rule["antecedent_text"],
                                       "consequent_text": rule["consequent_text"],
                                       "chained": not direct, "support": support})
                    violated.add(j)
                continue
            if cons_canon - fact_canon:  # consistent new consequent -> derive it
                fact_graph = _merge_graphs([fact_graph, rule["consequent"]])
                fact_canon = set(canonical_edges(fact_graph))
                fact_struct = _structured_edges(fact_graph)
                for e in cons_canon:
                    if e not in origin:  # a genuinely new fact
                        origin[e] = rtext
                        derivation[e] = {"rule": rtext, "step": steps, "support": support}
                        derived.append({"edge": e, "rule_index": j, "rule": rtext, "step": steps,
                                        "support": support})
                changed = True

    return {
        "given_facts": sorted(given_canon),
        "derived_facts": derived,
        "derivation": derivation,
        "violations": violations,
        "consistent": not violations,
        "steps": steps,
        "unparsed_facts": unparsed_facts,
        "unparsed_rules": unparsed_rules,
    }


def _proof_lines(edge: str, derivation: dict[str, dict], *, depth: int = 0,
                 seen: set[str] | None = None) -> list[str]:
    """Lines of a proof tree for ``edge`` back to the given (root) facts — each derived edge
    shows the rule and step that produced it, then recurses into its support; a leaf not in
    ``derivation`` is a given fact (a root). Cycles are guarded by ``seen``."""
    seen = seen if seen is not None else set()
    pad = "    " + "  " * depth
    d = derivation.get(edge)
    if d is None:
        return [f"{pad}{edge}  ·дано"]
    if edge in seen:
        return [f"{pad}{edge}  ·(см. выше)"]
    seen.add(edge)
    lines = [f"{pad}{edge}  ⇐ [шаг {d['step']}] «{d['rule']}»"]
    for s in d["support"]:
        lines += _proof_lines(s, derivation, depth=depth + 1, seen=seen)
    return lines


def explain(result: dict[str, Any], edge: str) -> list[str]:
    """Public: the proof tree for a (derived or given) edge in a forward_chain() result."""
    return _proof_lines(edge, result.get("derivation", {}))


_MARK = {
    "equivalent": "≡ ЭКВИВАЛЕНТНО", "entails": "⊨ A → B (A влечёт B)",
    "entailed_by": "⊨ B → A (B влечёт A)", "contradicts": "✗ ПРОТИВОРЕЧИЕ",
    "independent": "∥ НЕЗАВИСИМЫ", "unknown": "❓ НЕПРОВЕРЯЕМО",
}


def format_relation(result: dict[str, Any], *, indent: str = "  ") -> str:
    """Render a relate() result for a console (the audit artifact)."""
    lines = [
        f"{indent}A: «{result['a']['text']}»",
        f"{indent}B: «{result['b']['text']}»",
        f"{indent}{_MARK[result['verdict']]} — {result['reason']}",
    ]
    for c in result.get("conflicts", []):
        lines.append(f"{indent}  • [{c['class']}] {c['note']}")
    return "\n".join(lines)


def format_consistency(result: dict[str, Any], *, indent: str = "  ") -> str:
    """Render a check_consistency() result for a console."""
    head = "✓ СОГЛАСОВАНО" if result["consistent"] else "✗ ПРОТИВОРЕЧИВО"
    lines = [f"{indent}{head} ({result['checked']} из {result['statements']} разобрано)"]
    for c in result["contradictions"]:
        lines.append(f"{indent}  ✗ #{c['a_index']} «{c['a']}»  ⟂  #{c['b_index']} «{c['b']}»")
        for d in c["conflicts"]:
            lines.append(f"{indent}      • [{d['class']}] {d['note']}")
    for u in result["unparsed"]:
        lines.append(f"{indent}  ❓ #{u['index']} «{u['text']}» — не разобрано, исключено из проверки")
    return "\n".join(lines)


_RULE_MARK = {"violated": "✗ НАРУШЕНО", "satisfied": "✓ соблюдено", "inactive": "· не сработало",
              "fired_unknown": "? сработало, следствие не указано", "unparsed_rule": "❓ не разобрано"}


def format_rule_check(result: dict[str, Any], *, indent: str = "  ") -> str:
    """Render a check_against_rules() result for a console (the audit artifact)."""
    head = "✓ ПРАВИЛА СОБЛЮДЕНЫ" if result["consistent"] else "✗ НАРУШЕНИЕ ПРАВИЛ"
    lines = [f"{indent}{head} (фактов: {result['facts']}, правил: {result['rules']})"]
    for e in result["results"]:
        mark = _RULE_MARK.get(e["status"], e["status"])
        lines.append(f"{indent}  {mark}: «{e['text']}»")
        for d in e.get("conflicts", []):
            lines.append(f"{indent}      • [{d['class']}] {d['note']} — следствие опровергнуто фактами")
    for u in result["unparsed_facts"]:
        lines.append(f"{indent}  ❓ факт не разобран: «{u['text']}»")
    return "\n".join(lines)


def format_forward_chain(result: dict[str, Any], *, indent: str = "  ") -> str:
    """Render a forward_chain() result — derived facts (the inference trail) and any
    violations, flagging the multi-step (chained) ones — for a console audit artifact."""
    head = "✓ СОГЛАСОВАНО" if result["consistent"] else "✗ ПРОТИВОРЕЧИЕ ПРИ ВЫВОДЕ"
    lines = [f"{indent}{head} (шагов вывода: {result['steps']})"]
    if result["derived_facts"]:
        lines.append(f"{indent}  выведенные факты:")
        for d in result["derived_facts"]:
            lines.append(f"{indent}    +[шаг {d['step']}] {d['edge']}  ← «{d['rule']}»")
    else:
        lines.append(f"{indent}  новых фактов не выведено")
    derivation = result.get("derivation", {})
    for v in result["violations"]:
        tag = " (многошаговое)" if v.get("chained") else ""
        lines.append(f"{indent}  ✗ НАРУШЕНО{tag}: «{v['rule']}»")
        for d in v["conflicts"]:
            lines.append(f"{indent}      • [{d['class']}] {d['note']} — следствие опровергнуто фактами")
        if v.get("chained") and v.get("support"):  # show WHY the rule fired, back to roots
            lines.append(f"{indent}      цепочка вывода антецедента:")
            for s in v["support"]:
                lines += [f"  {ln}" for ln in _proof_lines(s, derivation)]
    for u in result["unparsed_facts"]:
        lines.append(f"{indent}  ❓ факт не разобран: «{u['text']}»")
    return "\n".join(lines)
