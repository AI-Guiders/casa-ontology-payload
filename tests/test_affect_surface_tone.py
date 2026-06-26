#!/usr/bin/env python3
"""Affect register reaches partner surface — duck probe + anti-oracle guard."""

from __future__ import annotations

from casa.domain.dialogue_bind.affect_surface import affect_register, apply_affect_register
from casa.domain.dialogue_bind.dialog_bind_policy import tone_register_slots
from casa.domain.partner_voice import partner_voice_invariant_violations
from casa.prisms.affect import affect_after_turn, spawn_emotional_zone
from casa.prisms.intelligence.character import spawn_character_zone
from casa.prisms.tick.discourse.model import ClauseSketch, DiscourseContext


def _state(*, security: float, valence: float = 0.0, repair: bool = False) -> dict:
    state: dict = {}
    spawn_emotional_zone(
        state,
        tick=1,
        config={"initial_axes": {"security": security, "valence": valence, "arousal": 0.2}},
    )
    if repair:
        affect_after_turn(state, "self_failure", tick=2)
    return state


def test_affect_register_secure_vs_insecure() -> None:
    from casa.prisms.affect import affect_compose_bias

    insecure = affect_register(affect_compose_bias(_state(security=0.3, repair=True)))
    secure = affect_register(affect_compose_bias(_state(security=0.72, valence=0.2)))
    assert insecure == "hedge"
    assert secure == "warm"
    assert insecure != secure


def test_apply_affect_register_changes_surface_and_stays_0078_clean() -> None:
    slots = tone_register_slots()
    allowed = {
        token.strip().lower()
        for key in ("hedge_opener", "hedge_linker", "warm_opener", "warm_linker")
        for token in (slots.get(key) or "").split("|")
        if token.strip()
    }

    state = _state(security=0.3, repair=True)
    clause = ClauseSketch(pieces=["настроение опишу по ходу"])
    ctx = DiscourseContext.bind("Как ты?", [], query_intent="social", state=state)
    before = " ".join(clause.pieces)
    key = apply_affect_register(clause, ctx)
    after = " ".join(clause.pieces)

    assert key == "hedge"
    assert after != before
    for token in after.lower().split():
        if token in allowed or token in before.lower():
            continue
        raise AssertionError(f"unexpected surface token not from bundle: {token}")
    assert partner_voice_invariant_violations(after) == []


def test_neutral_cold_boot_skips_register() -> None:
    state: dict = {}
    spawn_emotional_zone(state, tick=1)
    spawn_character_zone(state)
    from casa.prisms.affect import affect_compose_bias

    assert affect_register(affect_compose_bias(state)) is None
