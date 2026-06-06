#!/usr/bin/env python3
"""PDCA Act — centralized learning tail after Check (ADR-0034).

standardize: remember, retain, sleep, skill promote
adjust: Kolb revise
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from casa.domain.kolb_cycle import KolbContext, maybe_kolb_revise_tick
from casa.domain.pdca_cycle import pdca_act_kind
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.tick import ControlExtensions
from casa.prisms.memory.memory_prisms import run_sleep
from casa.prisms.shared.store_persist import mark_runtime_dirty
from casa.prisms.tick.agent_self_drive_tick import maybe_agent_self_drive_tick
from casa.prisms.tick.surprise_policy import (
    normalize_cue,
    should_skip_journal_surprise,
    surprise_signature,
)


@dataclass(frozen=True, slots=True)
class PdcaActConfig:
    remember_on_surprise: bool = True
    remember_min_value: float = 0.45
    retain_on_verified_predict: bool = True
    sleep_every: int = 0
    sleep_on_value: float = 1.0
    compact_persist_on_sleep: bool = False
    sleep_batch_size: int = 0
    kolb_relink_on_surprise: bool = True
    kolb_relink_min_value: float = 0.4
    agent_self_drive: bool = True
    agent_self_drive_min_value: float = 0.25
    surprise_min_value: float = 0.3


@dataclass(frozen=True, slots=True)
class PdcaActContext:
    store_dir: Path
    state: dict
    wm: WorkingMemory
    wm_next: WorkingMemory
    control: ControlExtensions
    mem_prep: dict[str, Any]
    cue: str
    bundle: dict | None
    hippo_ep: dict[str, Any] | None
    concept_ids: tuple[str, ...]
    cfg: PdcaActConfig


def maybe_agent_remember_surprise(
    store_dir: Path,
    state: dict,
    *,
    control: ControlExtensions,
    concept_ids: list[str],
    min_value: float,
    user_query: str | None = None,
    wm: WorkingMemory | None = None,
) -> dict[str, Any] | None:
    if control.value < min_value or not control.surprise:
        return None
    from casa.domain.partner_cue_policy import skip_deliberate_practice_for_cue

    cue = (user_query or (wm.goal if wm else "") or "macro_tick")[:120]
    if skip_deliberate_practice_for_cue(cue):
        return None
    cue = (user_query or (wm.goal if wm else "") or "macro_tick")[:120]
    norm = normalize_cue(cue)
    sig = surprise_signature(control.surprise)
    if should_skip_journal_surprise(store_dir, sig=sig):
        return None
    from casa.prisms.memory.agent_memory_ops import agent_remember

    return agent_remember(
        store_dir,
        state,
        {
            "kind": "observation",
            "text": (
                f"cue «{cue}»; predict mismatch: expected {', '.join(control.predicted[:5]) or '?'}; "
                f"surprise {', '.join(control.surprise[:5])}"
            ),
            "concepts": list(concept_ids[:8]),
            "tags": ["implicit", "surprise", f"cue:{norm[:48]}"],
            "data": {
                "prediction_error": control.prediction_error,
                "value": control.value,
                "surprise_signature": sig,
                "cue_normalized": norm,
            },
        },
        persist=False,
    )


def maybe_sleep_phase(
    state: dict,
    bundle: dict | None,
    *,
    sleep_every: int,
    sleep_on_value: float,
    control: ControlExtensions,
    store_dir: Path | None = None,
    compact_persist: bool | None = None,
    sleep_batch_size: int = 0,
) -> dict[str, Any] | None:
    from casa.prisms.memory.memory_prisms import hippo_episodes
    from casa.prisms.memory.sleep_job import clear_sleep_interrupt, note_sleep_batch, sleep_job_should_yield

    if sleep_job_should_yield(state):
        return None

    episodes = [e for e in hippo_episodes(state) if not e.get("consolidated")]
    if not episodes:
        return None

    cons = state.setdefault("consolidation", {})
    ticks_since = int(cons.get("ticks_since_sleep") or 0) + 1
    cons["ticks_since_sleep"] = ticks_since

    do_sleep = sleep_every > 0 and ticks_since >= sleep_every
    if not do_sleep and control.value >= sleep_on_value:
        do_sleep = True
    if not do_sleep and store_dir is not None:
        from casa.domain.load_governor import should_force_sleep_on_overload

        if should_force_sleep_on_overload(state):
            do_sleep = True
    if not do_sleep:
        return None

    if store_dir is not None:
        from casa.domain.load_governor import cognitive_load_from_state, retire_stuck_surprise_episodes

        load_rep = cognitive_load_from_state(state)
        retire_stuck_surprise_episodes(state, overloaded=bool(load_rep.get("overloaded")))

    batch = max(0, int(sleep_batch_size))
    max_ep = batch if batch > 0 else None
    rep = run_sleep(
        state,
        bundle,
        store_dir=store_dir,
        compact_persist=compact_persist,
        max_episodes=max_ep,
    )
    pending_after = len(hippo_episodes(state))
    if batch > 0:
        note_sleep_batch(state, pending_after=pending_after, merged=int(rep.get("merged") or 0), max_episodes=max_ep)
    if pending_after == 0:
        cons["ticks_since_sleep"] = 0
        clear_sleep_interrupt(state)
    mark_runtime_dirty(state)
    return rep


def maybe_pdca_act_tick(ctx: PdcaActContext) -> dict[str, Any]:
    """Run PDCA Act hooks in canonical order: remember → retain → sleep → adjust → self-drive."""
    cfg = ctx.cfg
    rep: dict[str, Any] = {
        "remember": None,
        "retain": None,
        "sleep": None,
        "adjust": None,
        "self_drive": None,
        "act_kind": None,
    }

    if cfg.remember_on_surprise:
        rep["remember"] = maybe_agent_remember_surprise(
            ctx.store_dir,
            ctx.state,
            control=ctx.control,
            concept_ids=list(ctx.concept_ids),
            min_value=cfg.remember_min_value,
            user_query=ctx.cue or None,
            wm=ctx.wm,
        )

    if cfg.retain_on_verified_predict and ctx.cue and ctx.bundle:
        from casa.prisms.memory.agent_autonomous_retain import maybe_autonomous_retain_tick

        rep["retain"] = maybe_autonomous_retain_tick(
            ctx.store_dir,
            ctx.state,
            cue=ctx.cue,
            bundle=ctx.bundle,
            persist=False,
        )

    if cfg.sleep_every > 0 or cfg.sleep_on_value > 0:
        if cfg.compact_persist_on_sleep:
            ctx.state.setdefault("store", {})["compact_persist_on_sleep"] = True
        rep["sleep"] = maybe_sleep_phase(
            ctx.state,
            ctx.bundle,
            sleep_every=cfg.sleep_every,
            sleep_on_value=cfg.sleep_on_value,
            control=ctx.control,
            store_dir=ctx.store_dir,
            compact_persist=True if cfg.compact_persist_on_sleep else None,
            sleep_batch_size=cfg.sleep_batch_size,
        )

    if cfg.kolb_relink_on_surprise and (ctx.hippo_ep or ctx.control.surprise):
        rep["adjust"] = maybe_kolb_revise_tick(
            KolbContext(
                store_dir=ctx.store_dir,
                state=ctx.state,
                wm=ctx.wm,
                control=ctx.control,
                hippo_ep=ctx.hippo_ep,
                cue=ctx.cue or "",
                min_surprise_value=cfg.kolb_relink_min_value,
            )
        )

    if cfg.agent_self_drive:
        rep["self_drive"] = maybe_agent_self_drive_tick(
            ctx.store_dir,
            ctx.state,
            wm=ctx.wm_next,
            control=ctx.control,
            mem_prep=ctx.mem_prep,
            cue=ctx.cue or "",
            bundle=ctx.bundle,
            min_drive_value=cfg.agent_self_drive_min_value,
        )

    kolb_revised = bool(rep["adjust"] and not (rep["adjust"] or {}).get("skipped"))
    skill_promoted = bool(
        rep["self_drive"]
        and (rep["self_drive"].get("skill_promote") or {}).get("promoted")
    )
    rep["act_kind"] = pdca_act_kind(
        kolb_revised=kolb_revised,
        skill_promoted=skill_promoted,
        sleep_ran=rep["sleep"] is not None,
        check_passed=not ctx.control.surprise and ctx.control.value < cfg.surprise_min_value,
    )
    return rep
