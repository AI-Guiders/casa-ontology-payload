#!/usr/bin/env python3
"""Compatibility facade over casa.domain.prism_wire (ADR-0020 M4).

New code should prefer FieldState / PrismCatalog; imports from this module remain valid.
"""

from __future__ import annotations

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
    ROOT_LEGACY,
    SCHEMA_CURRENT,
    SCHEMA_LEGACY,
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

_ACTIVE_CONTROL = "active_control_prism"
_ACTIVE_LEGACY = "active_cylinder"
_ACTIVE = "active_prism"

__all__ = [
    "SCHEMA_LEGACY",
    "SCHEMA_CURRENT",
    "ROOT_LEGACY",
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
    "_ACTIVE_CONTROL",
    "_ACTIVE_LEGACY",
    "_ACTIVE",
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
