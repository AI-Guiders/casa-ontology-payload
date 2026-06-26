"""Nervous subsystem — impulse trace (CASA-ADR-0080)."""

from casa.nervous.channels import ImpulseChannel, ImpulseOutcome
from casa.nervous.impulse import (
    DebugLevel,
    ImpulseRecorder,
    activate_impulse_trace,
    impulse_recorder,
    read_impulse_trace,
    resolve_debug_level,
)

__all__ = [
    "DebugLevel",
    "ImpulseChannel",
    "ImpulseOutcome",
    "ImpulseRecorder",
    "activate_impulse_trace",
    "impulse_recorder",
    "read_impulse_trace",
    "resolve_debug_level",
]
