#!/usr/bin/env python3
"""Intent Prism — full ADR-0057."""

from __future__ import annotations

from casa.prisms.memory.intent import (
    DEFAULT_INTENT_LATTICE,
    format_agent_tract_id,
    intent_after_partner_turn,
    intent_on_sleep_boundary,
    intent_root,
    intent_tract_boosts,
    is_agent_tract,
    list_agent_tracts,
    list_hypotheses,
    promote_intent_hypothesis,
    spawn_intent_lattice,
)
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.tick.discourse.composer import default_composer
from casa.prisms.tick.articulation_realize import UtterancePlan
from casa.prisms.tick.tract import compete_tract_intent


def _state():
    return ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 1})


def test_spawn_intent_lattice() -> None:
    state = _state()
    assert spawn_intent_lattice(state, tick=1) == "agent-intent-scratch"


def test_host_tract_learns_boost() -> None:
    state = _state()
    spawn_intent_lattice(state, tick=0)
    q = "Объясни позицию автора в этом тексте.\n\nПассаж про школу."
    intent, ranked = compete_tract_intent(q, None, state=state)
    intent_after_partner_turn(state, q, intent, tick=1, ranked=ranked, bind_top=30)
    intent_after_partner_turn(state, q, intent, tick=2, ranked=ranked, bind_top=32)
    assert intent_tract_boosts(state, q).get(intent, 0) >= 4


def test_emergent_tract_spawns_and_wins_argmax() -> None:
    state = _state()
    spawn_intent_lattice(state, tick=0)
    from casa.prisms.memory.agent_prism import ensure_agent_prism

    ensure_agent_prism(state)["intent_policy"] = {
        "emergent_activation_threshold": 2,
        "emergent_general_min_bind": 10,
    }
    q = "Расскажи про нашу вчерашнюю гипотезу про квантовую связь."
    for tick in range(1, 4):
        _, ranked = compete_tract_intent(q, None, state=state)
        intent_after_partner_turn(state, q, "general", tick=tick, ranked=ranked, bind_top=24)
    tracts = list_agent_tracts(state)
    assert tracts
    intent_id = str(tracts[0]["intent_id"])
    assert is_agent_tract(intent_id)
    intent2, ranked2 = compete_tract_intent(q, None, state=state)
    assert intent2 == intent_id
    assert any("intent_prism" in s for t in ranked2 for s in t.sources)


def test_promote_hypothesis_to_agent_tract() -> None:
    state = _state()
    spawn_intent_lattice(state, tick=0)
    q = "Обсудим аргументацию автора."
    intent, ranked = compete_tract_intent(q, None, state=state)
    for tick in range(3):
        intent_after_partner_turn(state, q, intent, tick=tick, ranked=ranked, bind_top=28)
    hyps = list_hypotheses(state)
    assert hyps
    hid = str(hyps[0]["hypothesis_id"])
    from casa.prisms.memory.intent import intent_root

    root = intent_root(state)[DEFAULT_INTENT_LATTICE]["hypotheses"][hid]
    root["score"] = 0.7
    rep = promote_intent_hypothesis(state, hid, target="agent", compose_mode="discuss")
    assert rep["target"] == "agent"
    assert list_agent_tracts(state)


def test_agent_tract_compose_via_registry() -> None:
    state = _state()
    slug = "test-discuss"
    intent_id = format_agent_tract_id(slug)
    from casa.prisms.memory.intent import agent_tracts

    agent_tracts(state)[slug] = {
        "intent_id": intent_id,
        "slug": slug,
        "compose_mode": "general",
        "score": 0.7,
        "geometry": ["question_mark"],
        "cue_tokens": ["обсудим"],
    }
    profile = {"intent_id": intent_id, "slug": slug, "compose_mode": "general"}
    blocks = [{"concept_id": "ru.prop.topic.x", "text": "тезис", "score": 40, "source": "kb"}]
    body = default_composer().compose(
        UtterancePlan(act="discuss", intent="general", atoms=[]),
        "Обсудим тезис.",
        blocks,
        query_intent=intent_id,
        agent_tract_profile=profile,
    )
    assert body is None or isinstance(body, str)


def test_sleep_prunes_weak_hypotheses() -> None:
    state = _state()
    spawn_intent_lattice(state, tick=0)
    root = intent_root(state)[DEFAULT_INTENT_LATTICE]
    root["hypotheses"] = {
        "weak:geo": {"tract_id": "social", "geometry": ["x"], "cue_tokens": ["a"], "score": 0.1, "tier": "scratch"},
        "strong:geo": {"tract_id": "discuss", "geometry": ["y"], "cue_tokens": ["b"], "score": 0.8, "tier": "scratch"},
    }
    rep = intent_on_sleep_boundary(state)
    assert rep["pruned"] >= 1
    assert rep["kept"] >= 1
