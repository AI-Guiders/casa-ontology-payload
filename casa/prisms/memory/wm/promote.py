"""Working Memory Prism — promotion and probe session reset."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.prisms.memory.agent_journal import append_journal_entry
from casa.prisms.memory.agent_memory_ops import agent_remember
from casa.prisms.memory.agent_prism import agent_lattices, ensure_agent_prism, place_agent_token
from casa.prisms.memory.memory_prisms import append_episode
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state

from .lattice import delete_wm_lattice, ensure_wm_scratch_lattice, wm_root
from .model import DEFAULT_SCRATCH_LATTICE, WM_SCENE_TAG, slug
from .policy import get_wm_policy


def promote_edge_to_hippo_episode(
    state: dict,
    edge: dict[str, Any],
    *,
    lattice_id: str,
) -> dict[str, Any] | None:
    fc = str(edge.get("from_concept") or "")
    tc = str(edge.get("to_concept") or "")
    if not fc or not tc:
        return None
    ep = append_episode(
        state,
        cue=f"wm:{fc}↔{tc}",
        surface_attempt=fc,
        correct=tc,
        lattice_id=lattice_id,
        concept_id=fc,
        scene=WM_SCENE_TAG,
        bind_class="wm_edge",
        links=[
            {"src": fc, "relation": "wm_link", "dst": tc},
            {"src": tc, "relation": "wm_link", "dst": fc},
        ],
        episode_source="wake",
    )
    if ep:
        edge["tier"] = "episode"
        edge["hippo_episode_id"] = ep.get("id")
    return ep


def promote_wm_edge(
    store_dir: Path,
    state: dict,
    edge_id: str,
    *,
    relation_kind: str = "link",
    persist: bool = True,
) -> dict[str, Any]:
    edge: dict[str, Any] | None = None
    for meta in wm_root(state).values():
        edge = (meta.get("edges") or {}).get(edge_id)
        if edge:
            break
    if not edge:
        raise KeyError(f"unknown wm edge: {edge_id}")
    policy = get_wm_policy(state, store_dir)
    sigma = float(edge.get("score") or 0.0)
    if sigma < float(policy.get("theta_promote", 0.65)):
        raise ValueError(f"edge score {sigma} below theta_promote")

    fc = str(edge.get("from_concept") or "")
    tc = str(edge.get("to_concept") or "")
    rel_slug = slug(f"{fc}-{tc}", max_len=40)
    world_rel = f"agent.world.relation.{relation_kind}.{rel_slug}"
    world_idea = f"agent.world.idea.{rel_slug}"
    text = f"Связь в мире: {fc} — {relation_kind} — {tc}."

    result = agent_remember(
        store_dir,
        state,
        {
            "kind": "hypothesis",
            "text": text,
            "concepts": [world_rel, world_idea, fc, tc],
            "tags": ["wm_promote", "agent.world"],
            "tokens": [world_rel, fc, tc],
        },
        persist=False,
    )
    append_journal_entry(
        store_dir,
        {
            "kind": "observation",
            "text": text,
            "concepts": [world_rel, fc, tc],
            "tags": ["wm_promote", "agent.world"],
            "meta": {"wm_edge_id": edge_id, "score": sigma, "relation_kind": relation_kind},
        },
        domain="self",
    )
    for meta in wm_root(state).values():
        meta.get("edges", {}).pop(edge_id, None)
    result["promoted"] = world_rel
    result["world_idea"] = world_idea
    result["wm_edge_id"] = edge_id
    if persist:
        mark_runtime_dirty(state)
        save_runtime_state(store_dir, state, force=True)
    return result


def promote_wm_edge_to_canon(
    store_dir: Path,
    state: dict,
    edge_id: str,
    *,
    law_label: str = "wm_law",
    persist: bool = True,
) -> dict[str, Any]:
    """Promote high-confidence WM cluster to agent canon lattice (immutable-lattice-canon pattern)."""
    world = promote_wm_edge(store_dir, state, edge_id, relation_kind=law_label, persist=False)
    canon_id = f"agent.law.{slug(law_label, max_len=32)}"
    ensure_wm_scratch_lattice(state, tick=int(state.get("field_version") or 0))
    place_agent_token(state, DEFAULT_SCRATCH_LATTICE, canon_id, copies=2, radius=2)
    world["canon_token"] = canon_id
    if persist:
        mark_runtime_dirty(state)
        save_runtime_state(store_dir, state, force=True)
    return world


def reset_wm_probe_session(store_dir: Path, state: dict) -> None:
    """Isolate WM probe: clear dialogue ring + scratch lattice metadata."""
    from casa.prisms.control.fpn_state import read_session_meta, write_session_meta

    meta = read_session_meta(store_dir)
    meta["dialogue_turns"] = []
    write_session_meta(store_dir, meta)
    if DEFAULT_SCRATCH_LATTICE in agent_lattices(state):
        delete_wm_lattice(state, DEFAULT_SCRATCH_LATTICE)
    block = ensure_agent_prism(state)
    block.pop("wm_topics", None)
    block.pop("wm_active_topic", None)
