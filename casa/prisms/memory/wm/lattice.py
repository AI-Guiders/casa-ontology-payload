"""Working Memory Prism — lattice lifecycle and metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.domain.prism_wire import prism_agent
from casa.prisms.memory.agent_prism import (
    agent_lattices,
    create_agent_lattice,
    delete_agent_lattice,
    ensure_agent_prism,
)

from .model import DEFAULT_SCRATCH_LATTICE, DEFAULT_SCRATCH_TTL, WM_CONCEPT_PREFIX, slug
from .policy import get_wm_policy


def wm_root(state: dict) -> dict[str, Any]:
    ensure_agent_prism(state)
    return prism_agent(state).setdefault(
        "wm_lattices",
        {},
    )


def lattice_meta(state: dict, lattice_id: str) -> dict[str, Any]:
    root = wm_root(state)
    meta = root.setdefault(
        lattice_id,
        {
            "lattice_id": lattice_id,
            "meta_id": f"agent.wm.lattice.{slug(lattice_id.replace('agent-wm-', ''))}",
            "spawned_tick": 0,
            "last_tick": 0,
            "ttl_ticks": DEFAULT_SCRATCH_TTL,
            "topic_id": None,
            "nodes": {},
            "edges": {},
        },
    )
    if not isinstance(meta.get("nodes"), dict):
        meta["nodes"] = {}
    if not isinstance(meta.get("edges"), dict):
        meta["edges"] = {}
    return meta


def _active_topic(state: dict) -> dict[str, Any] | None:
    block = ensure_agent_prism(state)
    topic_id = block.get("wm_active_topic")
    topics = block.get("wm_topics") or {}
    if topic_id and isinstance(topics, dict):
        row = topics.get(topic_id)
        if isinstance(row, dict):
            return row
    return None


def _set_active_topic(state: dict, topic_id: str, *, slug_text: str, tick: int) -> dict[str, Any]:
    block = ensure_agent_prism(state)
    topics = block.setdefault("wm_topics", {})
    lattice_id = f"agent-wm-topic-{slug(slug_text, max_len=20)}"
    row = topics.setdefault(
        topic_id,
        {
            "topic_id": topic_id,
            "meta_id": f"agent.wm.topic.{slug(slug_text, max_len=24)}",
            "slug": slug_text,
            "lattice_id": lattice_id,
            "spawned_tick": tick,
        },
    )
    block["wm_active_topic"] = topic_id
    return row


def infer_topic_slug(focus_concepts: list[str]) -> str:
    if not focus_concepts:
        return "session"
    head = focus_concepts[0]
    return slug(head.rsplit(".", 1)[-1], max_len=20)


def spawn_wm_lattice(
    state: dict,
    *,
    tick: int,
    overloaded: bool = False,
    topic_slug: str | None = None,
    force_new: bool = False,
) -> str | None:
    """Spawn or reuse scratch / topic lattice (ADR-0055)."""
    if overloaded:
        for lid in (DEFAULT_SCRATCH_LATTICE,):
            if lid in agent_lattices(state):
                return lid
        return None

    policy = get_wm_policy(state)
    root = wm_root(state)
    if len(root) >= int(policy.get("max_scratch_lattices") or 3) and not force_new:
        if DEFAULT_SCRATCH_LATTICE in agent_lattices(state):
            return DEFAULT_SCRATCH_LATTICE

    slug_text = topic_slug or "scratch"
    if slug_text == "scratch" and not force_new:
        lid = DEFAULT_SCRATCH_LATTICE
        if lid not in agent_lattices(state):
            create_agent_lattice(state, lid, width=32, height=32, concept_prefix=WM_CONCEPT_PREFIX)
            meta = lattice_meta(state, lid)
            meta["spawned_tick"] = tick
            meta["ttl_ticks"] = int(policy.get("scratch_ttl_ticks") or DEFAULT_SCRATCH_TTL)
        return lid

    topic_id = f"agent.wm.topic.{slug(slug_text, max_len=24)}"
    topic = _set_active_topic(state, topic_id, slug_text=slug_text, tick=tick)
    lid = str(topic["lattice_id"])
    if lid not in agent_lattices(state):
        create_agent_lattice(state, lid, width=32, height=32, concept_prefix=WM_CONCEPT_PREFIX)
        meta = lattice_meta(state, lid)
        meta["spawned_tick"] = tick
        meta["topic_id"] = topic_id
        meta["ttl_ticks"] = int(policy.get("scratch_ttl_ticks") or DEFAULT_SCRATCH_TTL)
    return lid


def ensure_wm_scratch_lattice(state: dict, *, tick: int = 0) -> str:
    out = spawn_wm_lattice(state, tick=tick, topic_slug="scratch")
    if not out:
        raise RuntimeError("WM scratch lattice unavailable (overload freeze?)")
    return out


def prune_wm_lattice(
    state: dict,
    *,
    tick: int,
    store_dir: Path | None = None,
    aggressive: bool = False,
) -> dict[str, Any]:
    policy = get_wm_policy(state, store_dir)
    theta = float(policy.get("theta_decay", 0.20))
    if aggressive:
        theta = min(0.35, theta + 0.10)
    removed: list[str] = []
    kept_total = 0
    expired_lattices: list[str] = []
    root = wm_root(state)

    for lid, meta in list(root.items()):
        ttl = int(meta.get("ttl_ticks") or DEFAULT_SCRATCH_TTL)
        spawned = int(meta.get("spawned_tick") or 0)
        if spawned and tick - spawned > ttl and lid != DEFAULT_SCRATCH_LATTICE:
            expired_lattices.append(lid)
            continue
        edges = meta.get("edges") or {}
        kept: dict[str, Any] = {}
        for eid, edge in edges.items():
            if str(edge.get("tier")) == "episode" and float(edge.get("score") or 0) >= float(
                policy.get("theta_hold", 0.45)
            ):
                kept[eid] = edge
                continue
            if float(edge.get("score") or 0.0) < theta:
                removed.append(eid)
            else:
                kept[eid] = edge
        meta["edges"] = kept
        kept_total += len(kept)
        meta["last_prune_tick"] = tick

    for lid in expired_lattices:
        delete_wm_lattice(state, lid)

    if removed or expired_lattices:
        state["field_version"] = int(state.get("field_version") or 0) + 1
    return {"removed": removed, "kept": kept_total, "expired_lattices": expired_lattices}


def delete_wm_lattice(state: dict, lattice_id: str) -> bool:
    root = wm_root(state)
    root.pop(lattice_id, None)
    block = ensure_agent_prism(state)
    topics = block.get("wm_topics") or {}
    if isinstance(topics, dict):
        for tid, row in list(topics.items()):
            if isinstance(row, dict) and row.get("lattice_id") == lattice_id:
                topics.pop(tid, None)
                if block.get("wm_active_topic") == tid:
                    block["wm_active_topic"] = None
    from casa.prisms.memory.agent_bridges import agent_bridges, remove_agent_bridge

    for bridge in list(agent_bridges(state)):
        if (bridge.get("from") or {}).get("lattice_id") == lattice_id and bridge.get("id"):
            remove_agent_bridge(state, str(bridge["id"]))
    return delete_agent_lattice(state, lattice_id)


def list_wm_state(state: dict) -> dict[str, Any]:
    lattices: list[dict[str, Any]] = []
    for lid, meta in sorted(wm_root(state).items()):
        edges = meta.get("edges") or {}
        lattices.append(
            {
                "lattice_id": lid,
                "meta_id": meta.get("meta_id"),
                "topic_id": meta.get("topic_id"),
                "node_count": len(meta.get("nodes") or {}),
                "edge_count": len(edges),
                "edges": [
                    {
                        "edge_id": eid,
                        "score": edge.get("score"),
                        "tier": edge.get("tier"),
                        "from": edge.get("from_concept"),
                        "to": edge.get("to_concept"),
                        "activations": len(edge.get("activations") or []),
                        "modalities": edge.get("modalities"),
                        "hippo_episode_id": edge.get("hippo_episode_id"),
                    }
                    for eid, edge in sorted(
                        edges.items(),
                        key=lambda kv: float(kv[1].get("score") or 0),
                        reverse=True,
                    )
                ],
            }
        )
    block = ensure_agent_prism(state)
    return {
        "active_topic": block.get("wm_active_topic"),
        "topics": block.get("wm_topics") or {},
        "lattices": lattices,
    }
