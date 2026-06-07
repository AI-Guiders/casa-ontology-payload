"""Working Memory Prism — node/edge placement and bridges."""

from __future__ import annotations

from typing import Any

from casa.domain.prism_ids import PRISM_AGENT
from casa.prisms.memory.agent_prism import place_agent_token

from .lattice import ensure_wm_scratch_lattice, lattice_meta
from .model import slug


def node_id_for_concept(concept_id: str) -> str:
    tail = concept_id.rsplit(".", 1)[-1]
    return f"agent.wm.node.{slug(tail)}"


def modality_for_concept(concept_id: str) -> str:
    cid = str(concept_id or "")
    if cid.startswith("math."):
        return "math"
    if cid.startswith(("passage.", "ru.prop.", "lang.word.")):
        return "text"
    if cid.startswith(("agent.world.", "vis.", "math.entity.", "math.role.")):
        return "vis"
    return "dialogue"


def place_wm_node(
    state: dict,
    concept_id: str,
    *,
    tick: int,
    lattice_id: str | None = None,
    token: str | None = None,
    modality: str | None = None,
) -> dict[str, Any]:
    cid = str(concept_id or "").strip()
    if not cid:
        raise ValueError("concept_id is required")
    lid = lattice_id or ensure_wm_scratch_lattice(state, tick=tick)
    node_id = node_id_for_concept(cid)
    tok = str(token or node_id).strip()
    place_agent_token(state, lid, tok, copies=1, radius=3)
    meta = lattice_meta(state, lid)
    nodes = meta["nodes"]
    row = nodes.setdefault(
        node_id,
        {
            "concept_id": cid,
            "activations": [],
            "modalities": [],
        },
    )
    if tick not in row["activations"]:
        row["activations"].append(tick)
    mod = modality or modality_for_concept(cid)
    mods = row.setdefault("modalities", [])
    if mod and mod not in mods:
        mods.append(mod)
    meta["last_tick"] = tick
    return {"node_id": node_id, "concept_id": cid, "lattice_id": lid, "modality": mod}


def edge_id(node_a: str, node_b: str) -> str:
    a, b = sorted([node_a, node_b])
    return f"agent.wm.edge.{slug(a.replace('agent.wm.node.', ''))}-{slug(b.replace('agent.wm.node.', ''))}"


def register_wm_bridge(state: dict, lattice_id: str, edge_id_text: str, from_node: str, to_node: str) -> None:
    from casa.prisms.memory.agent_bridges import add_agent_bridge

    try:
        add_agent_bridge(
            state,
            from_lattice=lattice_id,
            to_prism=PRISM_AGENT,
            to_lattice=lattice_id,
            relation="wm_co_place",
            tokens=[f"E:{edge_id_text}|wm|{from_node}|{to_node}"],
            bridge_id=f"ab-wm-{slug(edge_id_text.replace('agent.wm.edge.', ''), max_len=40)}",
            kind="agent_edge",
        )
    except (KeyError, ValueError):
        pass


def place_wm_edge(
    state: dict,
    from_concept: str,
    to_concept: str,
    *,
    tick: int,
    lattice_id: str | None = None,
    modality: str | None = None,
    surprise_before: int | None = None,
    surprise_after: int | None = None,
) -> dict[str, Any] | None:
    if from_concept == to_concept:
        return None
    lid = lattice_id or ensure_wm_scratch_lattice(state, tick=tick)
    mod = modality or modality_for_concept(from_concept)
    a = place_wm_node(state, from_concept, tick=tick, lattice_id=lid, modality=mod)
    b = place_wm_node(
        state,
        to_concept,
        tick=tick,
        lattice_id=lid,
        modality=modality or modality_for_concept(to_concept),
    )
    eid = edge_id(a["node_id"], b["node_id"])
    meta = lattice_meta(state, lid)
    edges = meta["edges"]
    edge = edges.setdefault(
        eid,
        {
            "from": a["node_id"],
            "to": b["node_id"],
            "from_concept": from_concept,
            "to_concept": to_concept,
            "score": 0.35,
            "activations": [],
            "modalities": [],
            "paste_turns": 0,
            "high_paste_turns": 0,
            "partner_hits": 0,
            "surprise_before": None,
            "surprise_after": None,
            "tier": "scratch",
            "hippo_episode_id": None,
        },
    )
    if tick not in edge["activations"]:
        edge["activations"].append(tick)
    mods = edge.setdefault("modalities", [])
    for m in (mod, modality_for_concept(to_concept)):
        if m and m not in mods:
            mods.append(m)
    if surprise_before is not None:
        edge["surprise_before"] = int(surprise_before)
    if surprise_after is not None:
        edge["surprise_after"] = int(surprise_after)
    register_wm_bridge(state, lid, eid, a["node_id"], b["node_id"])
    meta["last_tick"] = tick
    return {"edge_id": eid, "lattice_id": lid, **edge}
