#!/usr/bin/env python3
"""Situation fingerprint — a deterministic, language-independent handle for a meaning graph.

A meaning graph is a SET of typed edges over concepts, so it already has no word order.
This module turns it into:
  * a canonical edge list (sorted)                  — the situation's identity,
  * a stable integer id (hash of the canonical key) — the «отпечаток контекста»,
  * an additive bag-of-edges vector                 — for similarity and containment.

Because the graph lives on concepts, the fingerprint is identical across languages
(«яблоко на столе» == "apple on the table"), invariant to edge order, and invariant to
predicate synonymy (лежит/стоит/находится/на -> on via normalize_relation). And because
it is additive, a sub-situation is literally a sub-part: fingerprint("apple on table")
is contained in fingerprint("apple on table near window") — so situations form a partial
order (a lattice of situations).

Honest ceiling: turning free text into the canonical graph (predicate -> relation, role
assignment) is parsing — scoped to a controlled domain. The fingerprint itself is exact.
"""

from __future__ import annotations

import hashlib
from typing import Any

from casa.curriculum.concept_net import meaning_graph

# surface predicate (either language) -> canonical relation
PREDICATE_RELATION: dict[str, str] = {
    "на": "on", "лежит": "on", "лежать": "on", "стоит": "on", "стоять": "on",
    "находится": "on", "on": "on", "lies": "on", "stands": "on",
    "в": "in", "внутри": "in", "in": "in", "inside": "in",
    "у": "near", "около": "near", "рядом": "near", "near": "near", "by": "near", "beside": "near",
    "to": "in", "into": "in",  # destination of an action («save … to the folder» → in)
    "ест": "eat", "есть": "eat", "eat": "eat", "eats": "eat",
    "пьёт": "drink", "пьет": "drink", "пить": "drink", "drink": "drink", "drinks": "drink",
    "читает": "read", "читать": "read", "read": "read", "reads": "read",
    "из": "made_of", "of": "made_of",
    # software/UI actions — present 3sg + infinitive + imperative + English
    "открывает": "open", "открывать": "open", "открой": "open", "открывай": "open", "открыть": "open", "open": "open", "opens": "open",
    "закрывает": "close", "закрывать": "close", "закрой": "close", "закрывай": "close", "закрыть": "close", "close": "close", "closes": "close",
    "сохраняет": "save", "сохранять": "save", "сохрани": "save", "сохраняй": "save", "сохранить": "save", "save": "save", "saves": "save",
    "удаляет": "delete", "удалять": "delete", "удали": "delete", "удаляй": "delete", "удалить": "delete", "delete": "delete", "deletes": "delete",
    "нажимает": "click", "нажимать": "click", "нажми": "click", "нажимай": "click", "нажать": "click", "click": "click", "clicks": "click",
    "выбирает": "select", "выбирать": "select", "выбери": "select", "выбирай": "select", "выбрать": "select", "select": "select", "selects": "select",
    "изменяет": "edit", "изменять": "edit", "измени": "edit", "изменяй": "edit", "изменить": "edit", "edit": "edit", "edits": "edit",
    "показывает": "show", "показывать": "show", "показать": "show", "покажи": "show", "показывай": "show", "show": "show", "shows": "show", "display": "show", "displays": "show",
    "настраивает": "configure", "настраивать": "configure", "настроить": "configure", "настрой": "configure", "настраивай": "configure", "configure": "configure", "configures": "configure", "set": "configure", "sets": "configure", "установить": "configure", "устанавливает": "configure", "установи": "configure", "устанавливай": "configure",
    "копирует": "copy", "копировать": "copy", "скопировать": "copy", "скопируй": "copy", "копируй": "copy", "copy": "copy", "copies": "copy",
    "перемещает": "move", "перемещать": "move", "переместить": "move", "перемести": "move", "перемещай": "move", "move": "move", "moves": "move",
    "создаёт": "create", "создавать": "create", "создать": "create", "создай": "create", "создавай": "create", "create": "create", "creates": "create",
    "переименовать": "rename", "переименовывает": "rename", "переименуй": "rename", "переименовывай": "rename", "rename": "rename", "renames": "rename",
    "печатает": "print", "печатать": "print", "распечатать": "print", "напечатать": "print", "распечатай": "print", "печатай": "print", "print": "print", "prints": "print",
    "включает": "enable", "включать": "enable", "включить": "enable", "включи": "enable", "включай": "enable", "разрешить": "enable", "разреши": "enable", "enable": "enable", "enables": "enable",
    "install": "install", "installs": "install",
    "скачивает": "download", "скачивать": "download", "скачать": "download", "скачай": "download", "скачивай": "download", "загрузить": "download", "загрузи": "download", "download": "download", "downloads": "download",
    # English gerund headings — «Opening a file», «Configuring the proxy»
    "opening": "open", "closing": "close", "saving": "save", "deleting": "delete",
    "clicking": "click", "selecting": "select", "editing": "edit", "showing": "show",
    "configuring": "configure", "copying": "copy", "moving": "move", "creating": "create",
    "renaming": "rename", "printing": "print", "enabling": "enable", "installing": "install",
    "downloading": "download",
}


def normalize_relation(predicate: str) -> str:
    """Map a surface predicate to its canonical relation (synonyms collapse)."""
    return PREDICATE_RELATION.get(predicate.strip().lower(), predicate.strip().lower())


def _node_token(cid: str, nodes: dict[str, Any]) -> str:
    """A node's fingerprint token: concept id annotated with its adjective attributes,
    count and measure, so «red file» / «два файла» / «5 мл воды» are each DISTINCT from the
    bare concept (and «5 ml» ≠ «5 mg» ≠ «50 ml») in the key."""
    node = nodes.get(cid) or {}
    tok = cid
    if node.get("attrs"):
        tok += "[" + ",".join(sorted(node["attrs"])) + "]"
    cnt = node.get("count")
    if cnt and cnt != 1:
        tok += f"×{cnt}"
    m = node.get("measure")
    if m:
        tok += f"{{{m['value']}{m['unit']}}}"
    return tok


def _edge_key(rel: str, src: str, dst: str, polarity: str = "pos") -> str:
    # «¬» prefix makes a negated edge a DISTINCT situation: «X on table» ≠ «X not on table».
    return f"{'¬' if polarity == 'neg' else ''}{rel}({src},{dst})"


def canonical_edges(graph: dict[str, Any], *, satisfied_only: bool = True) -> list[str]:
    """Sorted canonical edge keys over CONCEPTS — language-independent, order-free. Polarity,
    adjective attributes and counts are all in the key, so a negated / modified / counted
    situation never collides with the bare one (the meaning is captured, not just relations)."""
    nodes = graph.get("nodes", {})
    out = [
        _edge_key(e["rel"], _node_token(e["src"], nodes), _node_token(e["dst"], nodes), e.get("polarity", "pos"))
        for e in graph.get("edges", [])
        if e.get("src") and e.get("dst") and (e.get("satisfied") or not satisfied_only)
    ]
    return sorted(set(out))


def fingerprint(graph: dict[str, Any], *, satisfied_only: bool = True) -> dict[str, Any]:
    """Deterministic fingerprint of a meaning graph: canonical key, stable integer id,
    and an additive bag-of-edges vector."""
    edges = canonical_edges(graph, satisfied_only=satisfied_only)
    key = " & ".join(edges)
    fid = int.from_bytes(hashlib.blake2b(key.encode("utf-8"), digest_size=8).digest(), "big")
    return {"key": key, "id": fid, "edges": edges, "vector": {e: 1 for e in edges}}


def same_situation(a: dict[str, Any], b: dict[str, Any], *, satisfied_only: bool = True) -> bool:
    """Do two graphs denote the same situation (identical canonical edge set)?"""
    return canonical_edges(a, satisfied_only=satisfied_only) == canonical_edges(b, satisfied_only=satisfied_only)


def contains(outer: dict[str, Any], inner: dict[str, Any], *, satisfied_only: bool = True) -> bool:
    """Is ``inner`` a sub-situation of ``outer`` (its edge set a subset)?"""
    return set(canonical_edges(inner, satisfied_only=satisfied_only)) <= set(
        canonical_edges(outer, satisfied_only=satisfied_only)
    )


def similarity(a: dict[str, Any], b: dict[str, Any], *, satisfied_only: bool = True) -> float:
    """Jaccard overlap of two situations' edge sets (1.0 = identical, 0.0 = disjoint)."""
    A = set(canonical_edges(a, satisfied_only=satisfied_only))
    B = set(canonical_edges(b, satisfied_only=satisfied_only))
    if not A and not B:
        return 1.0
    return len(A & B) / len(A | B)


def graph_from_predicates(
    state: dict, lattice_id: str, raw_triples: list[tuple[str, str, str]]
) -> dict[str, Any]:
    """Build a meaning graph from (predicate, figure, ground) triples, normalising
    predicate synonyms to canonical relations (лежит/стоит/на -> on). Role order
    (figure, ground) is assumed given — assigning it from free text is the parser's job."""
    triples = [(normalize_relation(p), x, y) for p, x, y in raw_triples]
    return meaning_graph(state, lattice_id, triples)


def situation_fingerprint(state: dict, lattice_id: str, raw_triples: list[tuple[str, str, str]]) -> dict[str, Any]:
    """Convenience: predicates -> normalised graph -> fingerprint."""
    return fingerprint(graph_from_predicates(state, lattice_id, raw_triples))


def gate_situation(
    state: dict,
    lattice_id: str,
    paraphrase_sets: list[list[list[tuple[str, str, str]]]],
    nested_pairs: list[tuple[list, list]],
    distinct_pairs: list[tuple[list, list]],
) -> dict[str, Any]:
    """Verify the fingerprint's three promises:
    - every phrasing in a paraphrase set yields ONE id (synonym/order/language invariance);
    - each (outer, inner) nests (contains holds one way, not the other);
    - each distinct pair has different fingerprints.
    """
    def fp_id(raw: list) -> int:
        return situation_fingerprint(state, lattice_id, raw)["id"]

    collapse = all(len({fp_id(p) for p in pset}) == 1 for pset in paraphrase_sets)
    nests = all(
        contains(graph_from_predicates(state, lattice_id, o), graph_from_predicates(state, lattice_id, i))
        and not contains(graph_from_predicates(state, lattice_id, i), graph_from_predicates(state, lattice_id, o))
        for o, i in nested_pairs
    )
    distinct = all(fp_id(a) != fp_id(b) for a, b in distinct_pairs)
    return {
        "passed": bool(collapse and nests and distinct and paraphrase_sets and nested_pairs and distinct_pairs),
        "paraphrases_collapse": collapse,
        "nesting_holds": nests,
        "distinct_differ": distinct,
    }
