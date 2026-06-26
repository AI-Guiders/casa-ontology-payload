#!/usr/bin/env python3
"""Motor speech efferent phase on life tick (ADR-0082)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.body.speech_tract import complete_efferent_plan, enqueue_efferent_plan
from casa.domain.motor_speech_plan import MotorSpeechPlan, new_plan_id
from casa.prisms.auditory.bridge_motor import bind_motor_heard_on_tick
from casa.prisms.control.sn_cen_runtime import TaskEmit
from casa.prisms.motor.self_listen import self_listen_from_plan
from casa.prisms.motor.speech_compose import compose_motor_units
from casa.prisms.motor.speech_disposition import resolve_motor_phonation_disposition
from casa.prisms.perceptual.zone import perceptual_merge_motor_self_echo


def maybe_motor_speech_on_tick(
    store_dir: Path,
    state: dict,
    *,
    tick: int,
    dialogue_rep: dict[str, Any] | None = None,
    task: TaskEmit | None = None,
    mem_prep: dict[str, Any] | None = None,
    self_drive_rep: dict[str, Any] | None = None,
    concept_hints: list[str] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Optional phonation efferent after compose — subject decides, silence is ok."""
    dialogue = dialogue_rep if isinstance(dialogue_rep, dict) else {}
    prep = mem_prep if isinstance(mem_prep, dict) else {}
    disposition = resolve_motor_phonation_disposition(
        store_dir,
        state,
        dialogue_rep=dialogue,
        task=task,
        mem_prep=prep,
        self_drive_rep=self_drive_rep,
        force=force,
    )
    if not disposition.should_phonate:
        return {"skipped": True, "reason": disposition.reason}

    units = compose_motor_units(
        state,
        tick=tick,
        intent=str(disposition.intent or "babble"),
        reply_text=disposition.reply_text,
        concept_hints=concept_hints,
    )
    if not units:
        return {"skipped": True, "reason": "empty_units", "agency": disposition.reason}

    plan = MotorSpeechPlan(
        plan_id=new_plan_id(tick=tick, salt="|".join(units[:2])),
        units=tuple(units),
        intent=str(disposition.intent or "babble"),
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
        "agency": disposition.reason,
    }
    perceptual_merge_motor_self_echo(
        state,
        plan_id=plan.plan_id,
        units=plan.units,
        base=state.get("_perceptual_turn"),
    )
    motor_bind = bind_motor_heard_on_tick(state)
    if store_dir is not None:
        from casa.nervous.sensory_hooks import record_motor_heard_bind_impulse

        record_motor_heard_bind_impulse(store_dir=store_dir, tick_id=tick, bind_rep=motor_bind)
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
        "agency": disposition.reason,
        "intent": disposition.intent,
        "plan": plan.to_dict(),
        "units": list(plan.units),
        "self_listen": listen_rep,
        "motor_bind": motor_bind,
    }
    if impulse:
        out["impulse"] = impulse
    return out
