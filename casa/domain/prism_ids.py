#!/usr/bin/env python3
"""Canonical prism and kind identifiers (ADR-0020 / ADR-0016)."""

from __future__ import annotations

SCHEMA_CURRENT = "multi_prism_v1"
ROOT = "prisms"

PRISM_MEMORY = "prism_memory"
PRISM_LANG_RU = "prism_lang_ru"
PRISM_MATH = "prism_math"
PRISM_HIPPO = "prism_hippo"
PRISM_CONTROL = "prism_control"
PRISM_AGENT = "prism_agent"
PRISM_HOT_CONTEXT = "prism_hot_context"
PRISM_ROUTER = "prism_router"
PRISM_VISUAL = "prism_visual"
PRISM_AUDITORY = "prism_auditory"
PRISM_CONTROL_VIS = "prism_control_vis"
PRISM_CONTROL_THALAMUS = "prism_control_thalamus"

PRISM_KIND_CONTENT = "content"
PRISM_KIND_HOT_CONTEXT = "hot_context"
PRISM_KIND_ROUTER = "router"
PRISM_KIND_CONTROL = "control"
PRISM_KIND_HIPPO = "hippo"

SN_ACTIVE_PRISM = "active_prism"
SN_ACTIVE_CONTROL = "active_control_prism"

SYSTEM_PRISM_IDS = frozenset({PRISM_HIPPO, PRISM_CONTROL, PRISM_AGENT})
