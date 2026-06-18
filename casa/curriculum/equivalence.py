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

    def mods(cid: str) -> tuple[tuple[str, ...], int]:
        n = nodes.get(cid) or {}
        return tuple(sorted(n.get("attrs") or [])), int(n.get("count") or 1)

    out = []
    for e in graph.get("edges", []):
        if not (e.get("src") and e.get("dst") and e.get("satisfied")):
            continue
        s_attrs, s_count = mods(e["src"])
        d_attrs, d_count = mods(e["dst"])
        out.append({
            "rel": e["rel"], "src": e["src"], "dst": e["dst"],
            "polarity": e.get("polarity", "pos"),
            "src_attrs": s_attrs, "src_count": s_count, "d_attrs": d_attrs, "d_count": d_count,
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
        if s["src_attrs"] != t["src_attrs"] or s["d_attrs"] != t["d_attrs"]:
            divs.append({"class": "attribute",
                         "note": f"«{rel}»: признаки {s['src_attrs'] or s['d_attrs']} vs {t['src_attrs'] or t['d_attrs']}"})

    for k in by_src.keys() - by_tgt.keys():
        divs.append({"class": "structure", "note": f"в переводе нет: {k[0]}({k[1].split('.')[-1]},{k[2].split('.')[-1]})"})
    for k in by_tgt.keys() - by_src.keys():
        divs.append({"class": "structure", "note": f"в источнике нет: {k[0]}({k[1].split('.')[-1]},{k[2].split('.')[-1]})"})
    return divs


def check_equivalence(state: dict, lattice_id: str, source: str, target: str) -> dict[str, Any]:
    """Triage whether ``target`` means the same as ``source``. See module docstring."""
    from casa.curriculum.parse import parse_graph
    from casa.curriculum.situation import canonical_edges

    sg, tg = parse_graph(state, lattice_id, source), parse_graph(state, lattice_id, target)
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
