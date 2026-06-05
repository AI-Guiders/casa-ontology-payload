#!/usr/bin/env python3
"""PDCA Check — centralized verify tail before Act (ADR-0034 / ADR-0036)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from casa.domain.goal_emergent import propose_goal_from_surprise
from casa.domain.goal_arbiter import arbitrate_check_intent
from casa.domain.hypothesis_queue import hypothesis_from_check, prune_hypothesis_queue
from casa.domain.metacog_gate import metacog_pre_check
from casa.domain.scaffold_fading import update_scaffold_after_check
from casa.domain.self_model import self_model_summary, update_tract_from_gate
from casa.domain.deliberate_practice import (
    apply_deliberate_practice,
    weakest_link_from_surprise,
)
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.tick import ControlExtensions
from casa.domain.prism_wire import prism_hippo
from casa.prisms.memory.memory_prisms import append_episode
from casa.prisms.shared.store_persist import mark_runtime_dirty
from casa.prisms.tick.surprise_policy import (
    bump_episode_recurrence,
    find_predict_mismatch_episode,
    normalize_cue,
)


@dataclass(frozen=True, slots=True)
class PdcaCheckConfig:
    surprise_episode: bool = True
    surprise_min_value: float = 0.3
    goal_from_surprise: bool = True
    metacog_gate: bool = True
    metacog_min_votes: int = 2
    deliberate_practice: bool = True


@dataclass(frozen=True, slots=True)
class PdcaCheckContext:
    store_dir: Path
    state: dict
    wm: WorkingMemory
    control: ControlExtensions
    cue: str
    lattice_id: str
    bundle: dict | None
    mem_prep: dict[str, Any]
    cfg: PdcaCheckConfig


def surprise_to_hippo_episode(
    state: dict,
    *,
    control: ControlExtensions,
    wm: WorkingMemory,
    user_query: str | None,
    lattice_id: str,
    bundle: dict | None,
    min_value: float,
) -> dict | None:
    if not control.surprise or control.value < min_value:
        return None
    cue = (user_query or wm.goal or "macro_tick")[:120]
    norm = normalize_cue(cue)
    existing = find_predict_mismatch_episode(state, norm_cue=norm)
    if existing:
        updated = bump_episode_recurrence(existing)
        updated["cue"] = cue
        episodes = prism_hippo(state).get("episodes") or []
        for i, row in enumerate(episodes):
            if row.get("id") == existing.get("id"):
                episodes[i] = updated
                break
        mark_runtime_dirty(state)
        return updated

    predicted = ", ".join(control.predicted[:8]) or "?"
    observed = ", ".join(control.surprise[:8]) or "?"
    ep = append_episode(
        state,
        cue=cue,
        surface_attempt=predicted,
        correct=observed,
        lattice_id=lattice_id,
        bundle=bundle,
        scene="predict_surprise",
        structure_tag="predict_mismatch",
    )
    mark_runtime_dirty(state)
    return ep


def maybe_pdca_check_tick(ctx: PdcaCheckContext) -> dict[str, Any]:
    """Check phase: hippo, hypothesis, self_model, arbiter."""
    cfg = ctx.cfg
    rep: dict[str, Any] = {
        "hippo_episode": None,
        "check_passed": False,
        "goal_emergent": None,
        "metacog": None,
        "deliberate_practice": None,
        "scaffold_level": None,
        "hypothesis": None,
        "self_model": None,
        "goal_arbiter": None,
    }

    if cfg.surprise_episode:
        rep["hippo_episode"] = surprise_to_hippo_episode(
            ctx.state,
            control=ctx.control,
            wm=ctx.wm,
            user_query=ctx.cue or None,
            lattice_id=ctx.lattice_id,
            bundle=ctx.bundle,
            min_value=cfg.surprise_min_value,
        )

    rep["check_passed"] = not ctx.control.surprise and ctx.control.value < cfg.surprise_min_value

    concept_id = ""
    if ctx.control.surprise:
        concept_id = str(ctx.control.surprise[0])
    elif ctx.wm.last_concepts:
        concept_id = str(ctx.wm.last_concepts[0])

    rep["hypothesis"] = hypothesis_from_check(
        ctx.state,
        cue=ctx.cue,
        concept_id=concept_id,
        passed=bool(rep["check_passed"]),
        tick=ctx.wm.tick,
    )
    prune_hypothesis_queue(ctx.state, tick=ctx.wm.tick)

    plan = ctx.mem_prep.get("plan_tick") if isinstance(ctx.mem_prep.get("plan_tick"), dict) else {}
    tract = str(plan.get("step_capability") or ctx.wm.step_capability or "")
    if tract:
        rep["self_model"] = update_tract_from_gate(
            ctx.state,
            tract,
            passed=bool(rep["check_passed"]),
            tick=ctx.wm.tick,
            provenance="tick_check",
        )

    rep["scaffold_level"] = update_scaffold_after_check(
        ctx.state,
        passed=bool(rep["check_passed"]),
    )

    if cfg.goal_from_surprise and ctx.control.surprise:
        rep["goal_emergent"] = propose_goal_from_surprise(
            ctx.store_dir,
            ctx.state,
            wm=ctx.wm,
            control=ctx.control,
            hippo_ep=rep["hippo_episode"],
            cue=ctx.cue,
        )

    deliberate: dict[str, Any] | None = None
    if cfg.deliberate_practice and not rep["check_passed"]:
        weak = weakest_link_from_surprise(ctx.control, hippo_ep=rep["hippo_episode"])
        if weak is None:
            stored = ctx.state.get("last_weakest_link")
            weak = stored if isinstance(stored, dict) else None
        deliberate = apply_deliberate_practice(ctx.wm, weak)

    rep["deliberate_practice"] = deliberate
    if str(ctx.wm.goal_id or "").startswith("goal.read.phrase") and rep["check_passed"]:
        from casa.domain.wake_decompose import advance_word_queue, current_word_focus

        rep["wake_decompose"] = advance_word_queue(ctx.state, passed=True)
        focus = current_word_focus(ctx.state, goal_id=ctx.wm.goal_id)
        if focus:
            ctx.wm.step_focus = focus

    rep["goal_arbiter"] = arbitrate_check_intent(
        ctx.state,
        ctx.wm,
        goal_emergent=rep["goal_emergent"],
        deliberate=deliberate,
    )

    if cfg.metacog_gate:
        rep["metacog"] = metacog_pre_check(
            ctx.state,
            step_capability=tract,
            min_votes=cfg.metacog_min_votes,
            gate_passed=rep["check_passed"],
        )

    rep["self_model_summary"] = self_model_summary(ctx.state)
    return rep
