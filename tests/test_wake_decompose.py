#!/usr/bin/env python3
"""Wake decompose phrase queue (ADR-0035 B7)."""

from __future__ import annotations

from casa.domain.wake_decompose import (
    advance_word_queue,
    init_phrase_queue,
    phrase_entry_for_goal,
    phrase_event_id_from_goal,
    phrase_words_for_goal,
)
from casa.prisms.memory.memory_prisms import ensure_prisms


def test_phrase_event_id_from_goal_suffix():
    assert phrase_event_id_from_goal("goal.read.phrase") == "lang.event.transitive.wash.v0"
    eid = "lang.event.ditransitive.give.v0"
    assert phrase_event_id_from_goal(f"goal.read.phrase#{eid}") == eid


def test_phrase_words_respect_event_suffix():
    words = phrase_words_for_goal("goal.read.phrase#lang.event.ditransitive.give.v0")
    roles = {w["role"] for w in words}
    assert "recipient" in roles
    assert len(words) == 4


def test_phrase_queue_advances_per_word():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    goal = "goal.read.phrase#lang.event.transitive.wash.v0"
    init_phrase_queue(state, goal)
    words = phrase_words_for_goal(goal)
    for i in range(len(words) - 1):
        rep = advance_word_queue(state, passed=True)
        assert rep.get("advanced") is True
        assert rep.get("word_index") == i + 1
    final = advance_word_queue(state, passed=True)
    assert final.get("complete") is True


def test_phrase_entry_for_goal():
    entry = phrase_entry_for_goal("goal.read.phrase#lang.event.transitive.wash.3sg_fem.v0")
    assert entry.get("event_id") == "lang.event.transitive.wash.3sg_fem.v0"
    agent = next(w for w in entry["words"] if w["role"] == "agent")
    assert agent["surface"] == "она"
