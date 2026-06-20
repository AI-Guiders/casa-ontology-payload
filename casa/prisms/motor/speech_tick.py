#!/usr/bin/env python3
"""Motor speech efferent phase on life tick (ADR-0082)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.body.speech_tract import complete_efferent_plan, enqueue_efferent_plan
from casa.domain.motor_speech_plan import MotorSpeechPlan, new_plan_id
from casa.prisms.auditory.bridge_motor import bind_motor_heard_on_tick
from casa.prisms.motor.self_listen import self_listen_from_plan
from casa.prisms.motor.speech_compose import compose_motor_units, motor_speech_enabled
from casa.prisms.perceptual.zone import perceptual_merge_motor_self_echo


def _pick_intent(
    *,
    babble: bool,
    reply_text: str | None,
    task_action: str | None,
) -> str | None:
    if babble:
        return "babble"
    if (reply_text or "").strip():
        return "parallel_compose"
    if task_action in {"speak", "articulate", "phonate"}:
        return "echo_field"
    return None


def maybe_motor_speech_on_tick(
    store_dir: Path,
    state: dict,
    *,
    tick: int,
    reply_text: str | None = None,
    concept_hints: list[str] | None = None,
    task_action: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Optional phonation efferent after compose — silence is ok."""
    cfg = state.setdefault("motor_speech", {})
    enabled = force or motor_speech_enabled(state)
    babble_only = bool(cfg.get("babble_only"))
    if not enabled:
        return {"skipped": True, "reason": "motor_speech_disabled"}

    intent = _pick_intent(
        babble=bool(cfg.get("babble") or babble_only),
        reply_text=reply_text,
        task_action=task_action,
    )
    if intent is None and not force:
        return {"skipped": True, "reason": "no_phonation_intent"}

    units = compose_motor_units(
        state,
        tick=tick,
        intent=str(intent or "babble"),
        reply_text=reply_text,
        concept_hints=concept_hints,
        max_units=int(cfg.get("max_units") or 4),
    )
    if not units:
        return {"skipped": True, "reason": "empty_units"}

    plan = MotorSpeechPlan(
        plan_id=new_plan_id(tick=tick, salt="|".join(units[:2])),
        units=tuple(units),
        intent=str(intent or "babble"),
        tick=tick,
    )
    enqueue_efferent_plan(store_dir, plan)
    listen_rep = self_listen_from_plan(state, plan, store_dir=store_dir)
    state["_motor_self_listen"] = {
        "plan_id": plan.plan_id,
        "aud_window_id": plan.self_listen_window_id,
        "units": list(plan.units),
        "tick": tick,
        "intent": plan.intent,
    }
    perceptual_merge_motor_self_echo(state, plan_id=plan.plan_id, units=plan.units, base=state.get("_perceptual_turn"))
    motor_bind = bind_motor_heard_on_tick(state)
    complete_efferent_plan(
        store_dir,
        plan.plan_id,
        heard_window_id=plan.self_listen_window_id,
        report={"self_listen": listen_rep, "motor_bind": motor_bind},
    )

    from casa.nervous.motor_speech_hooks import record_motor_speech_impulse

    impulse = record_motor_speech_impulse(
        store_dir=store_dir,
        plan=plan,
        listen_rep=listen_rep,
        motor_bind=motor_bind,
    )
    out: dict[str, Any] = {
        "spoken": True,
        "plan": plan.to_dict(),
        "units": list(plan.units),
        "self_listen": listen_rep,
        "motor_bind": motor_bind,
    }
    if impulse:
        out["impulse"] = impulse
    return out
