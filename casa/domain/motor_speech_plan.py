#!/usr/bin/env python3
"""Motor speech plan — field-native phonation units (ADR-0082), not TTS."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


MOTOR_SPEECH_SCENE_SELF = "self"
MOTOR_PLAN_PREFIX = "motor.plan."
MOTOR_UNIT_PREFIX = "motor.unit."


@dataclass(frozen=True, slots=True)
class MotorSpeechPlan:
    plan_id: str
    units: tuple[str, ...]
    intent: str
    tick: int
    scene_id: str = MOTOR_SPEECH_SCENE_SELF

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def concept_id(self) -> str:
        return motor_plan_concept_id(self.plan_id)

    @property
    def self_listen_window_id(self) -> str:
        return self_listen_window_id(self.plan_id)


def motor_plan_concept_id(plan_id: str) -> str:
    return f"{MOTOR_PLAN_PREFIX}{plan_id.strip()}"


def motor_unit_concept_id(unit: str) -> str:
    slug = "".join(ch if ch.isalnum() or ch in "._:-" else "_" for ch in unit.strip())
    return f"{MOTOR_UNIT_PREFIX}{slug or 'empty'}"


def self_listen_window_id(plan_id: str) -> str:
    return f"self-{plan_id.strip()}"


def self_listen_aud_concept_id(plan_id: str) -> str:
    return f"aud.window.{self_listen_window_id(plan_id)}"


def new_plan_id(*, tick: int, salt: str = "") -> str:
    raw = f"{tick}:{salt}:{uuid.uuid4().hex[:6]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def plan_from_dict(raw: dict[str, Any]) -> MotorSpeechPlan | None:
    if not isinstance(raw, dict):
        return None
    plan_id = str(raw.get("plan_id") or "").strip()
    if not plan_id:
        return None
    units_raw = raw.get("units") or []
    units = tuple(str(u).strip() for u in units_raw if str(u).strip())
    return MotorSpeechPlan(
        plan_id=plan_id,
        units=units,
        intent=str(raw.get("intent") or "babble"),
        tick=int(raw.get("tick") or 0),
        scene_id=str(raw.get("scene_id") or MOTOR_SPEECH_SCENE_SELF),
    )
