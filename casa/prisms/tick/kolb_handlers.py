#!/usr/bin/env python3
"""Domain-specific Kolb revise handlers — plug into domain-neutral kolb_cycle."""

from __future__ import annotations

from typing import Any

from casa.domain.kolb_cycle import KolbContext


def revise_crosslink_vis_lex(ctx: KolbContext) -> dict[str, Any] | None:
    """Literacy / visual tract: relink vis↔lex after mismatch."""
    from casa.prisms.tick.kolb_relink_tick import maybe_kolb_relink_tick

    rep = maybe_kolb_relink_tick(
        ctx.store_dir,
        ctx.state,
        wm=ctx.wm,
        control=ctx.control,
        hippo_ep=ctx.hippo_ep,
        cue=ctx.cue,
        min_surprise_value=ctx.min_surprise_value,
    )
    if rep is None or rep.get("skipped"):
        return rep
    return {**rep, "domain": "tract.vis_lex", "revise_kind": "relink_edge"}


def revise_math_pattern(ctx: KolbContext) -> dict[str, Any] | None:
    """Math tract: relink op hub or supersede count capability after mismatch."""
    math_obs = [str(c) for c in ctx.control.surprise if str(c).startswith("math.")]
    if not math_obs and not (ctx.hippo_ep and "math." in str(ctx.hippo_ep.get("correct") or "")):
        return None

    predicted_ops = [str(c) for c in ctx.control.predicted if str(c).startswith("math.")]
    target = math_obs[0] if math_obs else None
    if not target:
        return None

    from casa.domain.edge_relink import supersede_emergent_route
    from casa.domain.routing import ROUTE_KIND_CAPABILITY
    from casa.prisms.visual.bridge_math import agent_relink_crosslink, frame_id_from_vis_cue, vis_frame_concept_id

    plan_cap = (ctx.wm.step_capability or "").strip()
    if plan_cap.startswith("skill.math.") and predicted_ops and predicted_ops[0] != target:
        result = supersede_emergent_route(
            ctx.state,
            route_kind=ROUTE_KIND_CAPABILITY,
            match={"modality": "schema", "surface_class": "count"},
            gate="kolb:math_route_revise",
            target_skill="skill.math.count",
        )
        return {
            "domain": "tract.math_pattern",
            "revise_kind": "supersede_route",
            "new_target": target,
            "route_removed": result.route_removed,
            "route_added": result.route_added,
        }

    cue = (ctx.cue or "").strip()
    frame_id = frame_id_from_vis_cue(cue)
    if frame_id and predicted_ops:
        vis_cid = vis_frame_concept_id(frame_id)
        relink = agent_relink_crosslink(
            ctx.state,
            old_src=vis_cid,
            old_relation="co_occurs",
            old_dst=predicted_ops[0],
            new_src=vis_cid,
            new_relation="co_occurs",
            new_dst=target,
            gate="kolb:math_pattern",
            cue=cue,
            scene="kolb_math_pattern",
        )
        return {
            "domain": "tract.math_pattern",
            "revise_kind": "relink_math_bridge",
            **relink,
        }
    return {"domain": "tract.math_pattern", "revise_kind": "noop", "skipped": True}


def revise_route_capability(ctx: KolbContext) -> dict[str, Any] | None:
    """Any domain: supersede capability route when plan step implies wrong skill."""
    plan_cap = (ctx.wm.step_capability or "").strip()
    goal = (ctx.wm.goal_id or "").strip()
    if not plan_cap or not goal:
        return None
    if not ctx.control.surprise:
        return None

    alt_caps = [c for c in ctx.control.surprise if str(c).startswith("skill.")]
    if not alt_caps or alt_caps[0] == plan_cap:
        return None

    from casa.domain.edge_relink import supersede_emergent_route
    from casa.domain.routing import ROUTE_KIND_CAPABILITY

    match = {"modality": "vis", "locale": "ru"}
    if "novel" in goal or "analytic" in alt_caps[0]:
        match["novel"] = "true"

    result = supersede_emergent_route(
        ctx.state,
        route_kind=ROUTE_KIND_CAPABILITY,
        match=match,
        gate="kolb:tick_route_revise",
        target_skill=alt_caps[0],
    )
    return {
        "domain": "routing.capability",
        "revise_kind": "supersede_route",
        "old_skill": plan_cap,
        "new_skill": alt_caps[0],
        "route_removed": result.route_removed,
        "route_added": result.route_added,
    }
