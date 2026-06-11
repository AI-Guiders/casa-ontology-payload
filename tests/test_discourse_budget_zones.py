#!/usr/bin/env python3
"""Zone compose bias reaches efferent discourse budget."""

from __future__ import annotations

from casa.prisms.affect.zone import core_affect_state
from casa.prisms.intelligence.linguistic import ensure_linguistic_zone
from casa.prisms.tick.discourse.budget import discourse_budget_from_blocks


def _state_with_affect(*, arousal: float = 0.0, repair: float = 0.0) -> dict:
    state: dict = {}
    core = core_affect_state(state)
    core.axes.arousal = arousal
    core.episodic["dialog.repair_pending"] = repair
    zone = state.setdefault("intelligence", {}).setdefault("emotional", {})
    zone["core"] = core.to_dict()
    return state


def test_affect_budget_scale_widens_margin() -> None:
    blocks = [{"concept_id": "ru.dialog.affect", "score": 50}]
    low = discourse_budget_from_blocks(blocks, query_intent="social", stance="partial", state=_state_with_affect())
    high = discourse_budget_from_blocks(
        blocks, query_intent="social", stance="partial", state=_state_with_affect(arousal=0.8)
    )
    assert high.score_floor <= low.score_floor


def test_bind_only_blocks_do_not_dominate_social_floor() -> None:
    blocks = [
        {"concept_id": "subject.dialog.partner_recent", "score": 160},
        {"concept_id": "ru.dialog.affect", "score": 90},
    ]
    budget = discourse_budget_from_blocks(blocks, query_intent="social", stance="partial")
    assert budget.score_floor <= 90


def test_linguistic_confidence_widens_margin() -> None:
    blocks = [{"concept_id": "ru.dialog.self", "score": 48}]
    state: dict = {}
    ensure_linguistic_zone(state)["discourse_confidence"] = 0.3
    low = discourse_budget_from_blocks(blocks, query_intent="social", stance="partial", state=state)
    ensure_linguistic_zone(state)["discourse_confidence"] = 0.9
    high = discourse_budget_from_blocks(blocks, query_intent="social", stance="partial", state=state)
    assert high.score_floor <= low.score_floor
