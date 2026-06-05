#!/usr/bin/env python3
"""Kolb edge/route relink — weaken old binding, mint new (ADR-0034 step 5 → 2–3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from casa.domain.routing import RouteKind, Router


@dataclass
class RelinkResult:
    gate: str = ""
    weakened: dict[str, Any] = field(default_factory=dict)
    minted: dict[str, Any] | None = None
    episode_id: str | None = None
    route_removed: bool = False
    route_added: dict[str, Any] | None = None


def agent_relink_crosslink(
    state: dict,
    *,
    old_src: str,
    old_relation: str,
    old_dst: str,
    new_src: str,
    new_relation: str,
    new_dst: str,
    gate: str,
    cue: str = "",
    scene: str = "",
    weaken_copies: int | None = None,
    mint_copies: int = 5,
) -> RelinkResult:
    from casa.prisms.visual.bridge_math import agent_relink_crosslink as _relink

    raw = _relink(
        state,
        old_src=old_src,
        old_relation=old_relation,
        old_dst=old_dst,
        new_src=new_src,
        new_relation=new_relation,
        new_dst=new_dst,
        gate=gate,
        cue=cue,
        scene=scene,
        weaken_copies=weaken_copies,
        mint_copies=mint_copies,
    )
    return RelinkResult(
        gate=str(raw.get("gate") or gate),
        weakened=dict(raw.get("weakened") or {}),
        minted=raw.get("minted") if isinstance(raw.get("minted"), dict) else None,
        episode_id=str(raw.get("episode_id") or "") or None,
    )


def relink_vis_lex_bridge(
    state: dict,
    *,
    frame_id: str,
    old_lex_cid: str,
    new_lex_cid: str,
    gate: str,
    old_relation: str = "co_occurs",
    new_relation: str = "denotes",
    weaken_copies: int | None = None,
    mint_copies: int = 5,
) -> RelinkResult:
    from casa.prisms.visual.bridge_math import relink_vis_lex_bridge as _relink

    raw = _relink(
        state,
        frame_id=frame_id,
        old_lex_cid=old_lex_cid,
        new_lex_cid=new_lex_cid,
        gate=gate,
        old_relation=old_relation,
        new_relation=new_relation,
        weaken_copies=weaken_copies,
        mint_copies=mint_copies,
    )
    return RelinkResult(
        gate=str(raw.get("gate") or gate),
        weakened=dict(raw.get("weakened") or {}),
        minted=raw.get("minted") if isinstance(raw.get("minted"), dict) else None,
        episode_id=str(raw.get("episode_id") or "") or None,
    )


def supersede_emergent_route(
    state: dict,
    *,
    route_kind: RouteKind,
    match: dict[str, str],
    gate: str,
    agent_id: str = "",
    target_skill: str = "",
    target_goal: str = "",
    target_plan: str = "",
    steps: list[str] | None = None,
    target_prism: str = "",
    lattice_hint: str | None = None,
) -> RelinkResult:
    """Kolb: replace capability/applicability/goal route (not in-place rename)."""
    router = Router.bind(state)
    had_old = router.remove_route(match, route_kind=route_kind)
    route = router.add_emergent_route(
        route_kind=route_kind,
        match=match,
        gate=gate,
        agent_id=agent_id,
        target_skill=target_skill,
        target_goal=target_goal,
        target_plan=target_plan,
        steps=steps,
        target_prism=target_prism,
        lattice_hint=lattice_hint,
        extra_provenance={"supersedes": True},
    )
    return RelinkResult(
        gate=gate,
        route_removed=had_old,
        route_added=route.to_row(),
    )
