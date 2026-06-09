#!/usr/bin/env python3
"""agent-concept-core sparse index + NCA policy on hub edges only (ADR-0073 P19)."""

from __future__ import annotations

from typing import Any

from casa.prisms.memory.concept_layer import (
    CONCEPT_CORE_LATTICE,
    CONCEPT_PREFIX,
    bind_concept_id,
    canonical_concept_id,
    ensure_concept_domain,
    is_concept_hub,
    lex_for_locale,
)

INDEX_SCHEMA_VERSION = 1
HUB_TOKEN_PREFIX = "C:"
EDGE_TOKEN_PREFIX = "E:"

DEFAULT_NCA_POLICY: dict[str, Any] = {
    "lattice_id": CONCEPT_CORE_LATTICE,
    "hub_lambda": 0.0,
    "edge_lambda": 0.15,
    "protect_token_prefixes": [f"{HUB_TOKEN_PREFIX}{CONCEPT_PREFIX}"],
    "erosion_allowed_prefixes": [f"{EDGE_TOKEN_PREFIX}{CONCEPT_PREFIX}"],
    "skip_hub_erosion": True,
    "edges_only_repair": True,
}


def hub_token(concept_id: str) -> str:
    return f"{HUB_TOKEN_PREFIX}{canonical_concept_id(concept_id)}"


def edge_token(hub_id: str, target_id: str) -> str:
    hub = canonical_concept_id(hub_id)
    target = str(target_id or "").strip()
    return f"{EDGE_TOKEN_PREFIX}{hub}:{target}"


def concept_nca_policy(state: dict) -> dict[str, Any]:
    """NCA erosion policy — hub tokens λ=0; experiential edges may decay (P19)."""
    dom = ensure_concept_domain(state)
    stored = dom.get("nca_policy")
    if isinstance(stored, dict):
        return {**DEFAULT_NCA_POLICY, **stored}
    return dict(DEFAULT_NCA_POLICY)


def ensure_concept_index(state: dict) -> dict[str, Any]:
    dom = ensure_concept_domain(state)
    idx = dom.setdefault(
        "index",
        {
            "schema_version": INDEX_SCHEMA_VERSION,
            "lattice_id": CONCEPT_CORE_LATTICE,
            "hubs": {},
            "edge_count": 0,
        },
    )
    idx.setdefault("hubs", {})
    return idx


def _hub_edges_from_catalog(hub: str, catalog_row: dict[str, Any]) -> list[str]:
    edges: list[str] = []
    for loc, row in (catalog_row.get("lex") or {}).items():
        if not isinstance(row, dict):
            continue
        lex_id = str(row.get("concept_id") or "")
        if lex_id:
            edges.append(edge_token(hub, lex_id))
    for legacy in catalog_row.get("legacy_concept_ids") or []:
        edges.append(edge_token(hub, str(legacy)))
    for disc in (catalog_row.get("discourse") or {}).values():
        if disc:
            edges.append(edge_token(hub, str(disc)))
    return sorted(set(edges))


def index_concept_hub(
    state: dict,
    concept_id: str,
    *,
    tick: int | None = None,
) -> dict[str, Any]:
    """Place hub + lex edges on agent-concept-core; update sparse index."""
    from casa.prisms.memory.agent_prism import place_agent_token

    hub = canonical_concept_id(concept_id)
    if not hub.startswith(CONCEPT_PREFIX):
        raise ValueError(f"not a concept hub: {concept_id!r}")
    dom = ensure_concept_domain(state)
    catalog_row = (dom.get("catalog") or {}).get(hub) or {}
    ht = hub_token(hub)
    place_agent_token(state, CONCEPT_CORE_LATTICE, ht, copies=2)
    edges = _hub_edges_from_catalog(hub, catalog_row)
    placed_edges = 0
    for etok in edges:
        place_agent_token(state, CONCEPT_CORE_LATTICE, etok, copies=1)
        placed_edges += 1
    fv = int(tick if tick is not None else state.get("field_version") or 0)
    idx = ensure_concept_index(state)
    idx["hubs"][hub] = {
        "concept_id": hub,
        "hub_token": ht,
        "edges": edges,
        "edge_count": placed_edges,
        "indexed_at_tick": fv,
        "last_touch_tick": fv,
    }
    idx["edge_count"] = sum(int((h or {}).get("edge_count") or 0) for h in idx["hubs"].values())
    return {"concept_id": hub, "hub_token": ht, "edges": placed_edges}


def build_concept_hub_index(state: dict, *, tick: int | None = None) -> dict[str, Any]:
    """Rebuild index for all catalogued concept hubs (P19)."""
    dom = ensure_concept_domain(state)
    dom["nca_policy"] = concept_nca_policy(state)
    indexed: list[str] = []
    for hub in sorted(dom.get("concept_ids") or []):
        if not str(hub).startswith(CONCEPT_PREFIX):
            continue
        index_concept_hub(state, hub, tick=tick)
        indexed.append(str(hub))
    idx = ensure_concept_index(state)
    return {
        "indexed": len(indexed),
        "concept_ids": indexed,
        "edge_count": int(idx.get("edge_count") or 0),
        "lattice_id": CONCEPT_CORE_LATTICE,
    }


def touch_concept_hub_edges(
    state: dict,
    blocks: list[dict[str, Any]],
    *,
    tick: int | None = None,
) -> dict[str, Any]:
    """Strengthen experiential edges when bind activates a concept hub (not hub token)."""
    from casa.prisms.memory.agent_prism import place_agent_token

    touched_hubs = 0
    touched_edges = 0
    fv = int(tick if tick is not None else state.get("field_version") or 0)
    idx = ensure_concept_index(state)
    seen: set[str] = set()

    for row in blocks:
        if not isinstance(row, dict):
            continue
        hub = bind_concept_id(str(row.get("bind_hub") or row.get("concept_id") or ""))
        if not is_concept_hub(hub) or hub in seen:
            continue
        seen.add(hub)
        surface = str(row.get("surface_concept_id") or row.get("concept_id") or "")
        targets = [surface] if surface and surface != hub else []
        for loc in ("ru", "en"):
            lex_id = lex_for_locale(hub, loc)
            if lex_id:
                targets.append(lex_id)
        targets = sorted(set(t for t in targets if t))
        edge_tokens: list[str] = []
        for target in targets:
            etok = edge_token(hub, target)
            place_agent_token(state, CONCEPT_CORE_LATTICE, etok, copies=1)
            edge_tokens.append(etok)
            touched_edges += 1
        hub_row = idx["hubs"].setdefault(
            hub,
            {"concept_id": hub, "hub_token": hub_token(hub), "edges": [], "edge_count": 0},
        )
        merged_edges = sorted(set(list(hub_row.get("edges") or [])) | set(edge_tokens))
        hub_row["edges"] = merged_edges
        hub_row["edge_count"] = len(merged_edges)
        hub_row["last_touch_tick"] = fv
        touched_hubs += 1

    idx["edge_count"] = sum(int((h or {}).get("edge_count") or 0) for h in idx["hubs"].values())
    return {"touched_hubs": touched_hubs, "touched_edges": touched_edges, "tick": fv}


def nca_protected_tokens(state: dict, lattice_id: str = CONCEPT_CORE_LATTICE) -> set[str]:
    """Tokens that must not erode @ healthy agent (concept hub cells)."""
    if lattice_id != CONCEPT_CORE_LATTICE:
        return set()
    policy = concept_nca_policy(state)
    protected: set[str] = set()
    for hub, row in (ensure_concept_index(state).get("hubs") or {}).items():
        if isinstance(row, dict) and row.get("hub_token"):
            protected.add(str(row["hub_token"]))
        protected.add(hub_token(hub))
    for prefix in policy.get("protect_token_prefixes") or []:
        if prefix == f"{HUB_TOKEN_PREFIX}{CONCEPT_PREFIX}":
            continue
        protected.add(str(prefix))
    return protected


def nca_erosion_allowed_tokens(state: dict, lattice_id: str = CONCEPT_CORE_LATTICE) -> set[str]:
    """Edge tokens eligible for speed-3 erosion (P19 / ADR-0070 P15d hook)."""
    if lattice_id != CONCEPT_CORE_LATTICE:
        return set()
    allowed: set[str] = set()
    for row in (ensure_concept_index(state).get("hubs") or {}).values():
        if not isinstance(row, dict):
            continue
        for etok in row.get("edges") or []:
            allowed.add(str(etok))
    return allowed


def apply_concept_nca_edge_decay(
    state: dict,
    *,
    lattice_id: str = CONCEPT_CORE_LATTICE,
) -> dict[str, Any]:
    """Decay only E:concept.* edges; hub C:concept.* untouched (P19 minimal erosion)."""
    from casa.prisms.memory.agent_prism import agent_lattices

    if lattice_id not in agent_lattices(state):
        return {"skipped": True, "reason": "no_lattice"}
    policy = concept_nca_policy(state)
    protected = nca_protected_tokens(state, lattice_id)
    allowed = nca_erosion_allowed_tokens(state, lattice_id)
    lat = agent_lattices(state)[lattice_id]
    cells = lat.get("cells") or []
    decayed = 0
    kept_hub = 0
    alpha = float(policy.get("edge_lambda") or 0.15)
    new_cells: list[list[str]] = []
    for cell in cells:
        if not isinstance(cell, list):
            new_cells.append([])
            continue
        kept: list[str] = []
        for tok in cell:
            s = str(tok)
            if s in protected or s.startswith(f"{HUB_TOKEN_PREFIX}{CONCEPT_PREFIX}"):
                kept.append(s)
                kept_hub += 1
                continue
            if s in allowed or s.startswith(f"{EDGE_TOKEN_PREFIX}{CONCEPT_PREFIX}"):
                if alpha <= 0:
                    kept.append(s)
                else:
                    decayed += 1
                continue
            kept.append(s)
        new_cells.append(kept)
    lat["cells"] = new_cells
    rep = {
        "lattice_id": lattice_id,
        "hub_tokens_kept": kept_hub,
        "edges_decayed": decayed,
        "protected_count": len(protected),
        "policy": {"hub_lambda": policy.get("hub_lambda"), "edge_lambda": alpha},
    }
    forget = state.setdefault("forgetting", {})
    forget["concept_nca_last"] = rep
    return rep


def concept_index_snapshot(state: dict) -> dict[str, Any]:
    idx = ensure_concept_index(state)
    return {
        "schema_version": idx.get("schema_version"),
        "lattice_id": idx.get("lattice_id"),
        "hub_count": len(idx.get("hubs") or {}),
        "edge_count": int(idx.get("edge_count") or 0),
        "concept_ids": sorted((idx.get("hubs") or {}).keys()),
        "nca_policy": concept_nca_policy(state),
    }
