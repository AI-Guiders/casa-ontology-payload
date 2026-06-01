#!/usr/bin/env python3
"""Deprecated: use casa.domain.prism_ids and casa.domain.prism_wire (ADR-0020 M4)."""

from __future__ import annotations

import warnings

from casa.domain.prism_ids import (
    PRISM_AGENT,
    PRISM_CONTROL,
    PRISM_CONTROL_THALAMUS,
    PRISM_CONTROL_VIS,
    PRISM_HIPPO,
    PRISM_HOT_CONTEXT,
    PRISM_KIND_CONTENT,
    PRISM_KIND_CONTROL,
    PRISM_KIND_HOT_CONTEXT,
    PRISM_KIND_ROUTER,
    PRISM_LANG_RU,
    PRISM_MATH,
    PRISM_MEMORY,
    PRISM_ROUTER,
    PRISM_VISUAL,
    ROOT,
    SCHEMA_CURRENT,
)
from casa.domain.prism_wire import (
    active_control_prism_id,
    active_prism_id,
    normalize_prisms,
    prism_agent,
    prism_block,
    prism_control,
    prism_hippo,
    prism_hot_context,
    prism_kind,
    prism_memory,
    prism_router,
    prism_supports_lattices,
    prisms,
    set_active_control_prism,
    set_active_prism,
)

# Back-compat aliases for SN keys (not legacy wire).
_ACTIVE = "active_prism"
_ACTIVE_CONTROL = "active_control_prism"

__all__ = [
    "SCHEMA_CURRENT",
    "ROOT",
    "PRISM_MEMORY",
    "PRISM_LANG_RU",
    "PRISM_MATH",
    "PRISM_HIPPO",
    "PRISM_CONTROL",
    "PRISM_AGENT",
    "PRISM_HOT_CONTEXT",
    "PRISM_ROUTER",
    "PRISM_VISUAL",
    "PRISM_CONTROL_VIS",
    "PRISM_CONTROL_THALAMUS",
    "PRISM_KIND_CONTENT",
    "PRISM_KIND_HOT_CONTEXT",
    "PRISM_KIND_ROUTER",
    "PRISM_KIND_CONTROL",
    "_ACTIVE",
    "_ACTIVE_CONTROL",
    "normalize_prisms",
    "prisms",
    "prism_memory",
    "prism_hippo",
    "prism_control",
    "prism_agent",
    "prism_hot_context",
    "prism_router",
    "prism_block",
    "prism_kind",
    "prism_supports_lattices",
    "active_control_prism_id",
    "set_active_control_prism",
    "active_prism_id",
    "set_active_prism",
]


def __getattr__(name: str):
    if name in ("SCHEMA_LEGACY", "ROOT_LEGACY", "_ACTIVE_LEGACY"):
        warnings.warn(
            f"casa.prisms.shared.prism_state.{name} removed; legacy wire is internal to "
            "casa.domain.prism_wire.normalize_prisms",
            DeprecationWarning,
            stacklevel=2,
        )
        legacy = {
            "SCHEMA_LEGACY": "multi_cylinder_v1",
            "ROOT_LEGACY": "cylinders",
            "_ACTIVE_LEGACY": "active_cylinder",
        }
        return legacy[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
