#!/usr/bin/env python3
"""Unified probe + skill mastery gates."""

from __future__ import annotations

from casa.domain.emergent_promote import (
    promote_from_probe_report,
    promote_routes_from_probe_report,
    record_probe_gate,
)
from casa.domain.mastery_gate import (
    mastery_ready_for_skill,
    record_gate_attempt,
    skill_gate_id,
    sync_probe_pass_to_skill_gate,
)


def test_probe_sync_credits_skill_gate():
    state: dict = {}
    sync_probe_pass_to_skill_gate(state, "analytic-read-corpus-r1", tick=1)
    sync_probe_pass_to_skill_gate(state, "analytic-read-corpus-r1", tick=2)
    assert mastery_ready_for_skill(state, "skill.read.analytic", min_streak=2)


def test_tick_gate_and_probe_both_count():
    state: dict = {}
    record_gate_attempt(state, skill_gate_id("skill.read.analytic"), passed=True, tick=1)
    sync_probe_pass_to_skill_gate(state, "analytic-read-corpus-r1", tick=2)
    assert mastery_ready_for_skill(state, "skill.read.analytic", min_streak=2)


def test_intent_personal_probe_sync_credits_skill_gate():
    state: dict = {}
    sync_probe_pass_to_skill_gate(state, "probe_intent_personal_ru", tick=1)
    sync_probe_pass_to_skill_gate(state, "probe_intent_personal_ru", tick=2)
    assert mastery_ready_for_skill(state, "skill.tract.personal", min_streak=2)


def test_promote_from_probe_report_syncs_skill_gate():
    state: dict = {}
    event = {"phrase_know": True, "know_words": 3, "total_words": 3}
    report = {
        "probe": "phrase-agent-store",
        "promoted_skill": "skill.read.phrase",
        "phrase_know": True,
        "know_words": 3,
        "total_words": 3,
        "events": [event],
    }
    record_probe_gate(state, report, tick=1)
    record_probe_gate(state, report, tick=2)
    assert mastery_ready_for_skill(state, "skill.read.phrase", min_streak=2)


def test_mastery_gate_bootstrap_routes_still_require_streak():
    state: dict = {}
    report = {
        "probe": "literacy-corpus-quiz",
        "promoted_skill": "skill.read.whole",
        "know": 10,
        "total": 10,
        "matched": 10,
    }
    r1 = promote_from_probe_report(state, report, tick=1)
    assert r1.passed
    promote_from_probe_report(state, report, tick=2)
    r2 = promote_routes_from_probe_report(state, report, min_mastery_streak=2)
    assert r2.promoted
