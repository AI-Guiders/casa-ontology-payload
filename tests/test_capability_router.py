#!/usr/bin/env python3
"""Capability router hot path."""

from __future__ import annotations

from casa.domain.capability_router import build_capability_context, resolve_capability_skill
from casa.domain.emergent_promote import _safe_promote_capability
from casa.domain.routing import ROUTE_KIND_CAPABILITY, Router


def test_passage_context_geometry() -> None:
    ctx = build_capability_context("Маша купила хлеб.\n\nЧто купила?")
    assert ctx.geometry == "passage_context"
    assert ctx.modality == "text"


def test_spelling_intent_cue() -> None:
    ctx = build_capability_context("Как пишется: в течении или в течение дня?")
    assert ctx.read_intent == "spelling"


def test_resolve_promoted_comprehend_skill() -> None:
    state: dict = {"schema_version": "multi_prism_v1", "field_version": 0}
    _safe_promote_capability(
        state,
        match={"modality": "text", "geometry": "passage_context", "locale": "ru"},
        target_skill="skill.read.comprehend",
        gate="probe_text_meaning_ru",
        agent_id="von-neumann",
    )
    skill = resolve_capability_skill(state, "Маша купила хлеб.\n\nЧто купила?")
    assert skill == "skill.read.comprehend"


def test_router_geometry_match_field() -> None:
    state: dict = {"schema_version": "multi_prism_v1", "field_version": 0}
    _safe_promote_capability(
        state,
        match={"modality": "text", "geometry": "passage_context", "locale": "ru"},
        target_skill="skill.read.comprehend",
        gate="test",
        agent_id="t",
    )
    from casa.domain.routing import RouteContext

    tgt = Router.bind(state).resolve_layer(
        RouteContext(route_kind=ROUTE_KIND_CAPABILITY, modality="text", geometry="passage_context", locale="ru")
    )
    assert tgt is not None
    assert tgt.target_skill == "skill.read.comprehend"
