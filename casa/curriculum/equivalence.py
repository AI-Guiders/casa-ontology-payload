#!/usr/bin/env python3
"""Meaning-equivalence check — the validator spike.

Two sentences (a source and its translation, possibly cross-lingual) are parsed into
language-independent meaning graphs and their fingerprints compared. The output is a
THREE-state triage, never a bare yes/no:

  ✅ equivalent  — both parsed, fingerprints match (same situation).
  ⚠️ divergent   — both parsed, fingerprints differ → the divergence is classified and
                   shown (polarity / quantity / entity / relation / structure).
  ❓ uncheckable — at least one side did not parse to a situation → honest «can't verify».

The integrity of the tool is the third state: it NEVER reports «equivalent» when it merely
failed to parse one side. The divergence classes it CAN adjudicate exactly — polarity
(dropped «не»), quantity (5↔50), entity/relation — are precisely the dangerous, structured
errors where probabilistic LLM-judges are least reliable. Honest scope: only what the
controlled-domain parser covers; everything else is «uncheckable», by design.
"""

from __future__ import annotations

from typing import Any


def _structured_edges(graph: dict[str, Any]) -> list[dict[str, Any]]:
    """Satisfied edges with their node modifiers pulled in — for classification."""
    nodes = graph.get("nodes", {})

    def mods(cid: str) -> tuple[tuple[str, ...], int, tuple | None]:
        n = nodes.get(cid) or {}
        m = n.get("measure")
        return (tuple(sorted(n.get("attrs") or [])), int(n.get("count") or 1),
                (m["value"], m["unit"]) if m else None)

    out = []
    for e in graph.get("edges", []):
        if not (e.get("src") and e.get("dst") and e.get("satisfied")):
            continue
        s_attrs, s_count, s_meas = mods(e["src"])
        d_attrs, d_count, d_meas = mods(e["dst"])
        out.append({
            "rel": e["rel"], "src": e["src"], "dst": e["dst"],
            "polarity": e.get("polarity", "pos"),
            "src_attrs": s_attrs, "src_count": s_count, "src_meas": s_meas,
            "d_attrs": d_attrs, "d_count": d_count, "d_meas": d_meas,
        })
    return out


def _classify(src_edges: list[dict], tgt_edges: list[dict]) -> list[dict[str, str]]:
    """Align edges by their (rel, src, dst) skeleton and name how the modifiers differ."""
    def skel(e: dict) -> tuple[str, str, str]:
        return (e["rel"], e["src"], e["dst"])

    by_src = {skel(e): e for e in src_edges}
    by_tgt = {skel(e): e for e in tgt_edges}
    divs: list[dict[str, str]] = []

    for k in by_src.keys() & by_tgt.keys():  # same skeleton — compare modifiers
        s, t = by_src[k], by_tgt[k]
        rel = k[0]
        if s["polarity"] != t["polarity"]:
            divs.append({"class": "polarity",
                         "note": f"«{rel}»: источник {'отрицает' if s['polarity']=='neg' else 'утверждает'}, "
                                 f"перевод {'отрицает' if t['polarity']=='neg' else 'утверждает'} — потеряно отрицание"})
        if s["src_count"] != t["src_count"] or s["d_count"] != t["d_count"]:
            sc = s["d_count"] if s["src_count"] == t["src_count"] else s["src_count"]
            tc = t["d_count"] if s["src_count"] == t["src_count"] else t["src_count"]
            divs.append({"class": "quantity", "note": f"«{rel}»: количество {sc} vs {tc}"})
        sm = s["src_meas"] or s["d_meas"]
        tm = t["src_meas"] or t["d_meas"]
        if sm != tm:
            fmt = lambda m: f"{m[0]}{m[1]}" if m else "—"
            if sm and tm and sm[1] != tm[1]:  # units differ — the dangerous mg↔ml swap
                divs.append({"class": "unit", "note": f"«{rel}»: единица {sm[1]} vs {tm[1]}"})
            else:
                divs.append({"class": "quantity", "note": f"«{rel}»: мера {fmt(sm)} vs {fmt(tm)}"})
        if s["src_attrs"] != t["src_attrs"] or s["d_attrs"] != t["d_attrs"]:
            divs.append({"class": "attribute",
                         "note": f"«{rel}»: признаки {s['src_attrs'] or s['d_attrs']} vs {t['src_attrs'] or t['d_attrs']}"})

    # entity class: skeletons that differ ONLY in a named-entity node are a SWAPPED NAME
    # (Tamiflu ↔ Abilify) — the fourth dangerous class, not a structural mismatch
    from casa.curriculum.concept_net import NAMED_PREFIX

    def masked(k: tuple[str, str, str]) -> tuple:
        return tuple("«named»" if str(x).startswith(NAMED_PREFIX) else x for x in k)

    only_src = set(by_src.keys() - by_tgt.keys())
    only_tgt = set(by_tgt.keys() - by_src.keys())
    for ks in sorted(only_src):
        mate = next((kt for kt in sorted(only_tgt) if masked(kt) == masked(ks)), None)
        if mate is not None and any(str(x).startswith(NAMED_PREFIX) for x in ks):
            named_s = [x[len(NAMED_PREFIX):] for x in ks if str(x).startswith(NAMED_PREFIX)]
            named_t = [x[len(NAMED_PREFIX):] for x in mate if str(x).startswith(NAMED_PREFIX)]
            divs.append({"class": "entity",
                         "note": f"«{ks[0]}»: сущность {'/'.join(named_s)} vs {'/'.join(named_t)} — подменено имя"})
            only_src.discard(ks)
            only_tgt.discard(mate)

    for k in only_src:
        divs.append({"class": "structure", "note": f"в переводе нет: {k[0]}({k[1].split('.')[-1]},{k[2].split('.')[-1]})"})
    for k in only_tgt:
        divs.append({"class": "structure", "note": f"в источнике нет: {k[0]}({k[1].split('.')[-1]},{k[2].split('.')[-1]})"})
    return divs


def check_equivalence(state: dict, lattice_id: str, source: str, target: str,
                      langs: tuple[str | None, str | None] | None = None) -> dict[str, Any]:
    """Triage whether ``target`` means the same as ``source``. See module docstring.

    ``langs=(src_lang, tgt_lang)`` declares each side's language when the script cannot
    (EN↔ES are both Latin) — e.g. ``langs=("en", "es")`` for an EMEA pair."""
    from casa.curriculum.parse import parse_graph
    from casa.curriculum.situation import canonical_edges

    ls, lt = langs or (None, None)
    sg = parse_graph(state, lattice_id, source, lang=ls)
    tg = parse_graph(state, lattice_id, target, lang=lt)
    s_edges, t_edges = _structured_edges(sg), _structured_edges(tg)
    result: dict[str, Any] = {
        "source": {"text": source, "parsed": bool(s_edges), "edges": canonical_edges(sg)},
        "target": {"text": target, "parsed": bool(t_edges), "edges": canonical_edges(tg)},
        "divergences": [],
    }
    if not s_edges or not t_edges:
        side = "источник" if not s_edges else "перевод"
        result["verdict"] = "uncheckable"
        result["reason"] = f"не разобрана сторона: {side} — подтвердить эквивалентность нельзя"
        return result
    if set(result["source"]["edges"]) == set(result["target"]["edges"]):
        result["verdict"] = "equivalent"
        result["reason"] = "одинаковый граф смысла"
        return result
    result["verdict"] = "divergent"
    result["divergences"] = _classify(s_edges, t_edges)
    result["reason"] = "графы смысла различаются"
    return result


_MARK = {"equivalent": "✅ ЭКВИВАЛЕНТНО", "divergent": "⚠️ РАСХОЖДЕНИЕ", "uncheckable": "❓ НЕПРОВЕРЯЕМО"}


def format_check(result: dict[str, Any], *, indent: str = "  ") -> str:
    """Render a triage result for a console (the audit artifact)."""
    lines = [
        f"{indent}источник: «{result['source']['text']}»",
        f"{indent}перевод:  «{result['target']['text']}»",
        f"{indent}{_MARK[result['verdict']]} — {result['reason']}",
    ]
    for d in result.get("divergences", []):
        lines.append(f"{indent}  • [{d['class']}] {d['note']}")
    return "\n".join(lines)
