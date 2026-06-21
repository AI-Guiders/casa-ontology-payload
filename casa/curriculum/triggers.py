#!/usr/bin/env python3
"""Meaning triggers — fire on the CONTEXT extracted from a phrase, not on its words.

Dmitry's pre-LLM idea: instead of reacting to a specific word or phrase, key a trigger on
the «hash-code of a concept» — react when the expected MEANING is extracted, however it is
phrased (and in any language). The situation fingerprint is exactly that hash-code; a
trigger matches a meaning graph, so it fires across paraphrases and languages.

Three match modes (deterministic, auditable — you can always say WHY it fired):
  * exact      — the utterance's situation fingerprint equals the trigger's,
  * contains   — the trigger's sub-situation is present in the utterance (its edges are a
                 subset): «яблоко на столе» fires inside «яблоко на столе у окна»,
  * structural — the utterance is structurally analogous to the trigger (same relations,
                 type-compatible concept mapping): a pattern «agent eats food» fires on
                 «собака ест мясо» AND «человек ест яблоко».
"""

from __future__ import annotations

from typing import Any

from casa.curriculum.analogy import find_analogy
from casa.curriculum.parse import parse_graph
from casa.curriculum.situation import canonical_edges, fingerprint


def new_registry() -> dict[str, Any]:
    return {"triggers": []}


def register(
    registry: dict[str, Any], state: dict, lattice_id: str, *, pattern: str, label: str, mode: str = "contains"
) -> dict[str, Any]:
    """Register a trigger on the MEANING of ``pattern`` (a domain clause). ``mode`` is
    exact | contains | structural. Returns the stored trigger (or raises if unparseable)."""
    graph = parse_graph(state, lattice_id, pattern)
    edges = canonical_edges(graph)
    if not edges:
        raise ValueError(f"pattern did not parse to a meaning graph: {pattern!r}")
    trig = {"label": label, "mode": mode, "pattern": pattern, "edges": edges,
            "fid": fingerprint(graph)["id"], "graph": graph}
    registry["triggers"].append(trig)
    return trig


def fire(registry: dict[str, Any], state: dict, lattice_id: str, utterance: str) -> list[dict[str, Any]]:
    """Return the triggers fired by ``utterance`` (by meaning), each with why it matched."""
    graph = parse_graph(state, lattice_id, utterance)
    u_edges = set(canonical_edges(graph))
    if not u_edges:
        return []
    u_fid = fingerprint(graph)["id"]
    fired: list[dict[str, Any]] = []
    for t in registry["triggers"]:
        if t["mode"] == "exact":
            if u_fid == t["fid"]:
                fired.append({"label": t["label"], "mode": "exact", "why": t["pattern"]})
        elif t["mode"] == "structural":
            mapping = find_analogy(state, lattice_id, t["graph"], graph)
            if mapping is not None:
                fired.append({"label": t["label"], "mode": "structural", "why": t["pattern"], "mapping": mapping})
        else:  # contains
            if set(t["edges"]) <= u_edges:
                fired.append({"label": t["label"], "mode": "contains", "why": t["pattern"]})
    return fired


def labels(registry: dict[str, Any], state: dict, lattice_id: str, utterance: str) -> list[str]:
    """Convenience: just the labels fired by an utterance."""
    return [f["label"] for f in fire(registry, state, lattice_id, utterance)]
