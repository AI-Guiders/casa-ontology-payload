"""Motor speech efferent impulse trace (ADR-0082 + ADR-0080)."""

from __future__ import annotations

from typing import Any

from casa.domain.motor_speech_plan import MotorSpeechPlan
from casa.nervous.channels import ImpulseChannel, ImpulseOutcome
from casa.nervous.impulse import impulse_recorder


def record_motor_speech_impulse(
    *,
    store_dir,
    plan: MotorSpeechPlan,
    listen_rep: dict[str, Any],
    motor_bind: dict[str, Any] | None,
) -> dict[str, Any] | None:
    rec = impulse_recorder()
    if not rec.is_active:
        return None
    with rec.channel(ImpulseChannel.MOTOR_SPEECH, store_dir=store_dir) as imp:
        imp.select(
            "motor_plan",
            zone="motor",
            selected=list(plan.units),
            inputs={
                "plan_id": plan.plan_id,
                "intent": plan.intent,
                "tick": plan.tick,
            },
        )
        audio = listen_rep.get("self_listen") or {}
        imp.select(
            "self_listen",
            zone="auditory",
            selected=[str(listen_rep.get("aud_concept_id") or "")],
            inputs={
                "window_id": plan.self_listen_window_id,
                "duration_ms": audio.get("duration_ms"),
                "codec_id": audio.get("codec_id"),
            },
        )
        outcome = ImpulseOutcome.SPOKEN if listen_rep.get("self_listen") else ImpulseOutcome.NO_OP
        if motor_bind and motor_bind.get("bound"):
            outcome = ImpulseOutcome.COMPOSED
        summary = imp.finish(outcome, zones_touched=["motor", "auditory"])
        return dict(summary)
    return None
