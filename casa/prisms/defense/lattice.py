#!/usr/bin/env python3
"""Defense sandbox lattices — agent-owned scratch (ADR-0076 P20c, ADR-0014)."""

from __future__ import annotations

import re
from typing import Any

from casa.prisms.intelligence.defense_zone import SANDBOX_LATTICE, SANDBOX_PREFIX, ensure_defense_zone
from casa.prisms.memory.agent_prism import agent_lattices, create_agent_lattice, delete_agent_lattice, place_agent_token

DEFAULT_SCRATCH_TTL = 48
LAB_LATTICE_PREFIX = "agent-defense-lab-"


def slug(text: str, *, max_len: int = 20) -> str:
    raw = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (raw[:max_len] if raw else "lab")


def _zone_policy(state: dict) -> dict[str, Any]:
    return ensure_defense_zone(state).get("zone_policy") or {}


def defense_sandbox_lattices(state: dict) -> dict[str, Any]:
    zone = ensure_defense_zone(state)
    sandbox = zone.setdefault("sandbox", {})
    lats = sandbox.setdefault("lattices", {})
    if not isinstance(lats, dict):
        lats = {}
        sandbox["lattices"] = lats
    return lats


def defense_lattice_meta(state: dict, lattice_id: str) -> dict[str, Any]:
    lats = defense_sandbox_lattices(state)
    meta = lats.setdefault(
        lattice_id,
        {
            "lattice_id": lattice_id,
            "meta_id": f"agent.defense.lattice.{slug(lattice_id.replace(LAB_LATTICE_PREFIX, '').replace('agent-defense-', ''))}",
            "spawned_tick": 0,
            "last_tick": 0,
            "ttl_ticks": DEFAULT_SCRATCH_TTL,
            "topic_slug": "",
            "nodes": {},
            "edges": {},
        },
    )
    if not isinstance(meta.get("nodes"), dict):
        meta["nodes"] = {}
    if not isinstance(meta.get("edges"), dict):
        meta["edges"] = {}
    return meta


def _is_defense_sandbox_lattice(lattice_id: str) -> bool:
    lid = str(lattice_id or "")
    return lid == SANDBOX_LATTICE or lid.startswith(LAB_LATTICE_PREFIX)


def spawn_defense_scratch_lattice(
    state: dict,
    *,
    tick: int = 0,
    topic_slug: str | None = None,
    force_new: bool = False,
) -> str:
    """Spawn or reuse defense sandbox / lab lattice — never touches core."""
    ensure_defense_zone(state)
    policy = _zone_policy(state)
    max_lats = int(policy.get("max_sandbox_lattices") or 2)
    lats = defense_sandbox_lattices(state)
    slug_text = slug(topic_slug or "sandbox", max_len=18)

    if slug_text in ("sandbox", "rechannel") and not force_new:
        lid = SANDBOX_LATTICE
    else:
        lid = f"{LAB_LATTICE_PREFIX}{slug_text}"

    if lid not in agent_lattices(state):
        if len(lats) >= max_lats and not force_new:
            active = str(ensure_defense_zone(state).get("sandbox", {}).get("active_lattice") or SANDBOX_LATTICE)
            if active in agent_lattices(state):
                return active
            if SANDBOX_LATTICE in agent_lattices(state):
                return SANDBOX_LATTICE
        create_agent_lattice(
            state,
            lid,
            width=32,
            height=32,
            concept_prefix=SANDBOX_PREFIX,
        )
        meta = defense_lattice_meta(state, lid)
        meta["spawned_tick"] = int(tick)
        meta["topic_slug"] = slug_text
        meta["ttl_ticks"] = int(policy.get("scratch_ttl_ticks") or DEFAULT_SCRATCH_TTL)

    zone = ensure_defense_zone(state)
    zone.setdefault("sandbox", {})["active_lattice"] = lid
    defense_lattice_meta(state, lid)["last_tick"] = int(tick)
    return lid


def _concept_node_id(concept_id: str) -> str:
    tail = slug(concept_id.rsplit(".", 1)[-1], max_len=24)
    return f"agent.defense.node.{tail}"


def place_defense_node(
    state: dict,
    concept_id: str,
    *,
    tick: int = 0,
    lattice_id: str | None = None,
    role: str = "proxy",
) -> dict[str, Any]:
    """Place token on defense **sandbox** lattice only."""
    cid = str(concept_id or "").strip()
    if not cid:
        raise ValueError("concept_id is required")
    lid = lattice_id or spawn_defense_scratch_lattice(state, tick=tick)
    if not _is_defense_sandbox_lattice(lid):
        raise ValueError(f"not a defense sandbox lattice: {lid}")
    node_id = _concept_node_id(cid)
    place_agent_token(state, lid, node_id, copies=1, radius=3)
    meta = defense_lattice_meta(state, lid)
    row = meta["nodes"].setdefault(
        node_id,
        {"concept_id": cid, "role": str(role), "activations": []},
    )
    if int(tick) not in row["activations"]:
        row["activations"].append(int(tick))
    meta["last_tick"] = int(tick)
    return {"node_id": node_id, "concept_id": cid, "lattice_id": lid, "role": role}


def place_defense_rechannel_edge(
    state: dict,
    *,
    threat_concept: str,
    proxy_concept: str,
    tick: int = 0,
    lattice_id: str | None = None,
    weight: float = 0.5,
) -> dict[str, Any]:
    """Link threat cue node → proxy node on sandbox lattice."""
    lid = lattice_id or spawn_defense_scratch_lattice(state, tick=tick)
    threat = place_defense_node(state, threat_concept, tick=tick, lattice_id=lid, role="threat")
    proxy = place_defense_node(state, proxy_concept, tick=tick, lattice_id=lid, role="proxy")
    eid = f"agent.defense.edge.{slug(threat['node_id'])}-{slug(proxy['node_id'])}"
    meta = defense_lattice_meta(state, lid)
    edge = meta["edges"].setdefault(
        eid,
        {
            "from_node": threat["node_id"],
            "to_node": proxy["node_id"],
            "threat_concept": threat_concept,
            "proxy_concept": proxy_concept,
            "weight": round(float(weight), 4),
            "activations": [],
        },
    )
    if int(tick) not in edge["activations"]:
        edge["activations"].append(int(tick))
    meta["last_tick"] = int(tick)
    return {
        "edge_id": eid,
        "lattice_id": lid,
        "threat": threat,
        "proxy": proxy,
        "weight": edge["weight"],
    }


def prune_defense_scratch_lattices(state: dict, *, tick: int) -> dict[str, Any]:
    """Drop expired lab lattices (not default sandbox)."""
    policy = _zone_policy(state)
    ttl_default = int(policy.get("scratch_ttl_ticks") or DEFAULT_SCRATCH_TTL)
    removed: list[str] = []
    for lid, meta in list(defense_sandbox_lattices(state).items()):
        if lid == SANDBOX_LATTICE:
            continue
        spawned = int(meta.get("spawned_tick") or 0)
        ttl = int(meta.get("ttl_ticks") or ttl_default)
        if spawned and int(tick) - spawned > ttl:
            defense_sandbox_lattices(state).pop(lid, None)
            delete_agent_lattice(state, lid)
            removed.append(lid)
    return {"removed": removed, "tick": int(tick)}


def list_defense_sandbox_state(state: dict) -> dict[str, Any]:
    zone = ensure_defense_zone(state)
    sandbox = zone.get("sandbox") or {}
    lattices: list[dict[str, Any]] = []
    for lid, meta in sorted(defense_sandbox_lattices(state).items()):
        lattices.append(
            {
                "lattice_id": lid,
                "topic_slug": meta.get("topic_slug"),
                "node_count": len(meta.get("nodes") or {}),
                "edge_count": len(meta.get("edges") or {}),
                "spawned_tick": meta.get("spawned_tick"),
            }
        )
    return {
        "active_lattice": sandbox.get("active_lattice"),
        "experiments": len(sandbox.get("experiments") or []),
        "lattices": lattices,
    }


def lattice_evidence_score(state: dict, lattice_id: str) -> float:
    """0..1 evidence from sandbox edges for promote ceremony."""
    if not lattice_id or not _is_defense_sandbox_lattice(lattice_id):
        return 0.0
    meta = defense_lattice_meta(state, lattice_id)
    edges = meta.get("edges") or {}
    nodes = meta.get("nodes") or {}
    if not edges:
        return 0.0
    return min(1.0, 0.35 + 0.15 * len(edges) + 0.05 * len(nodes))
