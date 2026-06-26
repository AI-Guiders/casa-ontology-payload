#!/usr/bin/env python3
"""Structural analogy — «эта ситуация как та» by graph STRUCTURE, not shared concepts.

«кот на стуле» and «яблоко на столе» share NO concepts, yet they have the same relational
structure: on(X, Y) with X positionable and Y a support. An analogy is a consistent
bijection between the two graphs' concepts that turns one edge set into the other (same
relations, mapped endpoints) — Gentner-style structure mapping, deterministic and exact:

    find_analogy({on(cat,chair)}, {on(apple,table)}) -> {concept.cat: concept.apple, concept.chair: concept.table}

By default mapped concepts must be type-compatible (share a type in the network), so the
analogy is semantically sound (cat~apple are both physical objects; cat~idea is not).
recall_analogous finds stored situations with the same structure as a query, even when
they have no concept in common — relational retrieval on top of situation memory.
"""

from __future__ import annotations

import re
from typing import Any

from casa.curriculum.concept_net import isa_closure

_EDGE_RE = re.compile(r"^(\w+)\(([^,]+),([^)]+)\)$")


def _edges_of(graph: dict[str, Any]) -> list[tuple[str, str, str]]:
    return [(e["rel"], e["src"], e["dst"]) for e in graph.get("edges", []) if e.get("satisfied") and e.get("src") and e.get("dst")]


def edges_from_keys(keys: list[str]) -> list[tuple[str, str, str]]:
    """Parse canonical edge keys 'on(concept.apple,concept.table)' -> (rel, src, dst)."""
    out: list[tuple[str, str, str]] = []
    for k in keys:
        m = _EDGE_RE.match(k)
        if m:
            out.append((m.group(1), m.group(2), m.group(3)))
    return out


def _share_type(state: dict, lattice_id: str, a: str, b: str) -> bool:
    return bool(isa_closure(state, lattice_id, a) & isa_closure(state, lattice_id, b))


def _match(
    e1: list[tuple[str, str, str]],
    e2: list[tuple[str, str, str]],
    compat: Any,
) -> dict[str, str] | None:
    """Find a consistent bijection of concepts mapping edge set e1 onto e2."""
    if sorted(r for r, _, _ in e1) != sorted(r for r, _, _ in e2):
        return None
    used = [False] * len(e2)
    binding: dict[str, str] = {}

    def try_bind(a: str, b: str) -> bool:
        if a in binding:
            return binding[a] == b
        if b in binding.values() or not compat(a, b):
            return False
        binding[a] = b
        return True

    def solve(i: int) -> dict[str, str] | None:
        if i == len(e1):
            return dict(binding)
        r1, s1, d1 = e1[i]
        for j in range(len(e2)):
            if used[j] or e2[j][0] != r1:
                continue
            saved = dict(binding)
            if try_bind(s1, e2[j][1]) and try_bind(d1, e2[j][2]):
                used[j] = True
                res = solve(i + 1)
                if res is not None:
                    return res
                used[j] = False
            binding.clear()
            binding.update(saved)
        return None

    return solve(0) if e1 else None


def find_analogy(
    state: dict, lattice_id: str, g1: dict[str, Any], g2: dict[str, Any], *, type_compatible: bool = True
) -> dict[str, str] | None:
    """Return a concept mapping g1 -> g2 that preserves the relational structure, or None."""
    compat = (lambda a, b: _share_type(state, lattice_id, a, b)) if type_compatible else (lambda a, b: True)
    return _match(_edges_of(g1), _edges_of(g2), compat)


def analogous(state: dict, lattice_id: str, g1: dict[str, Any], g2: dict[str, Any], **kw: Any) -> bool:
    return find_analogy(state, lattice_id, g1, g2, **kw) is not None


def recall_analogous(
    state: dict, lattice_id: str, memory: dict[str, Any], query: dict[str, Any], *, type_compatible: bool = True
) -> list[tuple[dict[str, Any], dict[str, str]]]:
    """Stored situations whose STRUCTURE matches the query (same relations, type-compatible
    concept mapping) — analogies, even with no concept in common."""
    compat = (lambda a, b: _share_type(state, lattice_id, a, b)) if type_compatible else (lambda a, b: True)
    qe = _edges_of(query)
    out: list[tuple[dict[str, Any], dict[str, str]]] = []
    for rec in memory.get("situations", []):
        mapping = _match(qe, edges_from_keys(rec["edges"]), compat)
        if mapping is not None:
            out.append((rec, mapping))
    return out
