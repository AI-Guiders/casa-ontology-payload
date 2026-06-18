#!/usr/bin/env python3
"""Textual render of a meaning graph — make the language-independent core visible.

The round-trip demo's whole point is the MIDDLE: text becomes a graph of concepts
(language-independent), and the graph becomes text again. This renders that graph for a
console: concept nodes with their type/affordances and the relation edges between them.
The node labels are the concept ids' leaves (apple/table) — the same tokens whether the
sentence came in Russian or English, which is exactly the claim the demo makes.

Pure formatting over the dict that ``meaning_graph``/``parse_graph`` return; no state,
no I/O. Unsatisfied edges (a category error like «стол ест яблоко») render with ✗ and the
reason, so the same renderer serves the refusal showcase.
"""

from __future__ import annotations

import sys
from typing import Any


def ensure_utf8_console() -> None:
    """Make stdout/stderr emit UTF-8 and never crash on the box-drawing / Cyrillic glyphs.

    A legacy Windows console (cp866/cp1251) raises UnicodeEncodeError on '▶'/'═'/Cyrillic;
    ``errors='replace'`` degrades an unrenderable glyph to '?' instead of killing the run."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except Exception:
            pass

# generic types/affordances carried by nearly everything — hidden so the distinguishing
# ones stand out in the legend (every physical object is positionable/ownable).
_GENERIC_TYPES = {"physical_object"}
_GENERIC_AFFORDS = {"ownable", "positionable"}


def _leaf(concept: str) -> str:
    """The language-independent node label: the concept id's leaf (lex.apple -> apple)."""
    return concept.split(".")[-1]


def _node_label(concept: str, nodes: dict[str, Any]) -> str:
    """Concept leaf with adjective attributes and count: file -> file[red]×2."""
    node = nodes.get(concept) or {}
    label = _leaf(concept)
    if node.get("attrs"):
        label += "[" + ",".join(node["attrs"]) + "]"
    cnt = node.get("count")
    if cnt and cnt != 1:
        label += f"×{cnt}"
    m = node.get("measure")
    if m:
        label += f"{{{m['value']}{m['unit']}}}"
    return label


def _rel_label(edge: dict[str, Any]) -> str:
    """Relation with a polarity marker: a negated edge shows «¬» («not on»)."""
    return ("¬" if edge.get("polarity") == "neg" else "") + edge["rel"]


def _order_path(edges: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    """If the edges form one simple chain (a─▶b─▶c), return them in path order so the
    graph renders inline; otherwise None (caller renders one edge per line)."""
    if not edges:
        return None
    by_src = {e["src"]: e for e in edges}
    if len(by_src) != len(edges):
        return None  # a node has two out-edges -> not a simple chain
    dsts = {e["dst"] for e in edges}
    starts = [e["src"] for e in edges if e["src"] not in dsts]
    if len(starts) != 1:
        return None
    chain, node, seen = [], starts[0], set()
    while node in by_src and node not in seen:
        seen.add(node)
        e = by_src[node]
        chain.append(e)
        node = e["dst"]
    return chain if len(chain) == len(edges) else None


def render_graph(graph: dict[str, Any], *, indent: str = "  ") -> str:
    """Render the meaning graph as a labelled block: edges, then a node legend."""
    nodes = graph.get("nodes", {})
    edges = graph.get("edges", [])
    lines = [f"{indent}┌─ граф понятий (язык-независимый) ─"]
    if not edges:
        lines.append(f"{indent}│  (пусто — ни одного отношения)")
    else:
        chain = _order_path(edges)
        if chain:
            seq = _node_label(chain[0]["src"], nodes)
            for e in chain:
                tip = "▶" if e.get("satisfied") else "✗"
                seq += f" ──{_rel_label(e)}──{tip} {_node_label(e['dst'], nodes)}"
            lines.append(f"{indent}│  {seq}")
        else:
            for e in edges:
                tip = "▶" if e.get("satisfied") else "✗"
                lines.append(
                    f"{indent}│  {_node_label(e['src'], nodes)} ──{_rel_label(e)}──{tip} {_node_label(e['dst'], nodes)}"
                )
    # node legend: distinguishing type + affordances
    for cid in _legend_order(nodes, edges):
        node = nodes[cid]
        types = [t for t in node.get("types", []) if t not in _GENERIC_TYPES]
        affords = [a for a in node.get("affords", []) if a not in _GENERIC_AFFORDS]
        bits = f"{indent}│  · {_leaf(cid):<8} тип: {'/'.join(types) or '—'}"
        if affords:
            bits += f" · может: {', '.join(affords)}"
        lines.append(bits)
    # surface a category error inline so the refusal demo reads from the same block
    for e in edges:
        if not e.get("satisfied"):
            miss = (e.get("reason") or "").replace("missing:", "").strip("/")
            lines.append(f"{indent}│  ✗ «{e['rel']}» не выполнено (не хватает: {miss})")
    lines.append(f"{indent}└─")
    return "\n".join(lines)


def _legend_order(nodes: dict[str, Any], edges: list[dict[str, Any]]) -> list[str]:
    """Nodes in first-mention order along the edges, then any leftovers."""
    seen: list[str] = []
    for e in edges:
        for cid in (e["src"], e["dst"]):
            if cid in nodes and cid not in seen:
                seen.append(cid)
    seen += [cid for cid in nodes if cid not in seen]
    return seen


def render_round_trip(
    graph: dict[str, Any], *, source: str | None = None, ru: str | None = None,
    en: str | None = None, indent: str = "  ",
) -> str:
    """Full demo block: source phrase -> graph -> RU paraphrase + EN translation, with the
    'same graph from either language' note. ``ru``/``en`` are the realised sentences."""
    lines: list[str] = []
    if source is not None:
        lines.append(f"{indent}вход: «{source}»")
    lines.append(render_graph(graph, indent=indent))
    if ru:
        lines.append(f"{indent}→ RU: {ru}")
    if en:
        lines.append(f"{indent}→ EN: {en}")
    if ru and en:
        lines.append(f"{indent}   (один и тот же граф восстановлен и из RU, и из EN — смысл, не слова)")
    return "\n".join(lines)
