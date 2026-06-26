#!/usr/bin/env python3
"""Emergent motor↔heard bridges (ADR-0082, mirror bridge_vis)."""

from __future__ import annotations

from typing import Any

from casa.domain.auditory_tract import LATTICE_AUDIO_SPECTRUM
from casa.domain.motor_speech_plan import (
    MOTOR_PLAN_PREFIX,
    motor_plan_concept_id,
    self_listen_aud_concept_id,
    self_listen_window_id,
)
from casa.domain.prism_ids import PRISM_AUDITORY
from casa.domain.prism_wire import prism_block
from casa.prisms.auditory.bootstrap import ensure_prism_auditory
from casa.prisms.memory.f0_stack import strengthen_graph_edge
from casa.prisms.memory.memory_prisms import persist_content_lattices
from casa.prisms.memory.prism_hot_context import add_hot_edge
from casa.prisms.visual.bridge_math import DEFAULT_RELATION, _edge_token, bridge_exists_on_field

_AUD_SELF_PREFIX = "aud.window.self-"
_MAX_PAIRS = 48


def _motor_episodes(episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ep in episodes:
        cid = str(ep.get("concept_id") or "")
        if cid.startswith(MOTOR_PLAN_PREFIX):
            out.append(ep)
    return out


def _self_aud_episodes(episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ep in episodes:
        if str(ep.get("lattice_id") or "") != LATTICE_AUDIO_SPECTRUM:
            continue
        cid = str(ep.get("concept_id") or "")
        if cid.startswith(_AUD_SELF_PREFIX):
            out.append(ep)
    return out


def _plan_id_from_motor_cid(cid: str) -> str:
    return cid[len(MOTOR_PLAN_PREFIX) :]


def _matching_self_aud(motor_cid: str, aud_eps: list[dict[str, Any]]) -> dict[str, Any] | None:
    plan_id = _plan_id_from_motor_cid(motor_cid)
    target = self_listen_aud_concept_id(plan_id)
    for ep in aud_eps:
        if str(ep.get("concept_id") or "") == target:
            return ep
    return None


def bind_motor_heard_on_tick(state: dict, *, copies: int = 2) -> dict[str, Any] | None:
    """Life tick: mint motor↔self-heard co_occurs when efferent closed same tick."""
    block = state.get("_motor_self_listen")
    if not isinstance(block, dict):
        return None
    plan_id = str(block.get("plan_id") or "").strip()
    if not plan_id:
        return None
    motor_cid = motor_plan_concept_id(plan_id)
    aud_cid = self_listen_aud_concept_id(plan_id)
    row = mint_motor_heard_bridge(
        state,
        motor_cid=motor_cid,
        aud_cid=aud_cid,
        copies=copies,
        provenance="life_tick_motor_self",
    )
    if row:
        return {
            "bound": True,
            "motor_concept_id": motor_cid,
            "aud_concept_id": aud_cid,
            "extract": row,
        }
    from casa.prisms.memory.memory_prisms import memory_lattices

    lats = memory_lattices(state)
    if bridge_exists_on_field(lats, src=motor_cid, relation=DEFAULT_RELATION, dst=aud_cid, state=state):
        return {
            "bound": False,
            "already": True,
            "motor_concept_id": motor_cid,
            "aud_concept_id": aud_cid,
        }
    return None


def mint_motor_heard_bridge(
    state: dict,
    *,
    motor_cid: str,
    aud_cid: str,
    relation: str = DEFAULT_RELATION,
    copies: int = 4,
    provenance: str = "sleep_motor_heard",
) -> dict[str, str] | None:
    motor_cid = motor_cid.strip()
    aud_cid = aud_cid.strip()
    if not (motor_cid.startswith(MOTOR_PLAN_PREFIX) and aud_cid.startswith(_AUD_SELF_PREFIX)):
        return None
    from casa.prisms.memory.memory_prisms import memory_lattices

    lats = memory_lattices(state)
    if bridge_exists_on_field(lats, src=motor_cid, relation=relation, dst=aud_cid, state=state):
        return None
    ensure_prism_auditory(state)
    lats = memory_lattices(state)
    on_aud = strengthen_graph_edge(lats, LATTICE_AUDIO_SPECTRUM, aud_cid, relation, motor_cid, copies=copies)
    on_motor = strengthen_graph_edge(lats, LATTICE_AUDIO_SPECTRUM, motor_cid, relation, aud_cid, copies=copies)
    if not (on_aud or on_motor):
        return None
    add_hot_edge(state, motor_cid, relation, aud_cid, salience=1.0, provenance=provenance)
    persist_content_lattices(state, lats)
    aud_lat = (prism_block(state, PRISM_AUDITORY).get("lattices") or {}).get(LATTICE_AUDIO_SPECTRUM)
    if aud_lat:
        persist_content_lattices(state, {LATTICE_AUDIO_SPECTRUM: aud_lat})
    state["field_version"] = int(state.get("field_version") or 0) + 1
    return {
        "src": motor_cid,
        "relation": relation,
        "dst": aud_cid,
        "edge": _edge_token(motor_cid, relation, aud_cid),
        "on_auditory": on_aud,
        "on_motor": on_motor,
        "provenance": provenance,
    }


def extract_emergent_motor_heard_bridges(
    lattices: dict[str, dict],
    episodes: list[dict[str, Any]],
    state: dict,
    *,
    copies: int = 4,
) -> list[dict[str, Any]]:
    """Sleep extract: motor.plan.* + aud.window.self-* on shared scene."""
    _ = lattices
    motor_eps = _motor_episodes(episodes)
    aud_eps = _self_aud_episodes(episodes)
    if not motor_eps or not aud_eps:
        return []

    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for mep in motor_eps:
        motor_cid = str(mep.get("concept_id") or "")
        aud_ep = _matching_self_aud(motor_cid, aud_eps)
        if aud_ep is None:
            continue
        aud_cid = str(aud_ep.get("concept_id") or "")
        key = (motor_cid, aud_cid)
        if key in seen:
            continue
        seen.add(key)
        row = mint_motor_heard_bridge(
            state,
            motor_cid=motor_cid,
            aud_cid=aud_cid,
            copies=copies,
            provenance="sleep_motor_heard",
        )
        if row:
            out.append(
                {
                    "episode_id": str(mep.get("id") or aud_ep.get("id") or ""),
                    "kind": "emergent_motor_heard",
                    "motor_concept_id": motor_cid,
                    "aud_concept_id": aud_cid,
                    "plan_id": _plan_id_from_motor_cid(motor_cid),
                    "self_window_id": self_listen_window_id(_plan_id_from_motor_cid(motor_cid)),
                    "extract": row,
                }
            )
        if len(seen) >= _MAX_PAIRS:
            return out
    return out
