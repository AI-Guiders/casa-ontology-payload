"""Efferent channel ids and outcomes (CASA-ADR-0080)."""

from __future__ import annotations

from enum import StrEnum


class ImpulseChannel(StrEnum):
    LISTEN_IMPRINT = "listen_imprint"
    PARTNER_DIALOGUE = "partner_dialogue"
    IDLE_EFFERENT = "idle_efferent"
    MOTOR_COMPOSE = "motor_compose"
    VISION_GATE = "vision_gate"
    CONTROL_ROUTING = "control_routing"
    SLEEP_TRAIN = "sleep_train"


class ImpulseOutcome(StrEnum):
    SPOKEN = "spoken"
    SILENT = "silent"
    DEFERRED = "deferred"
    BLOCKED = "blocked"
    ERROR = "error"
    NO_OP = "no_op"
    COMPOSED = "composed"
    FRAME_SELECTED = "frame_selected"
    HOLD = "hold"
    MODE_CHANGED = "mode_changed"
    QUEUED = "queued"
    SKIPPED = "skipped"
