#!/usr/bin/env python3
from __future__ import annotations

from casa.domain.emergent_promote import promote_from_probe_report, promote_routes_from_probe_report
from casa.domain.mastery_gate import mastery_ready, record_gate_attempt
from casa.prisms.memory.memory_prisms import ensure_prisms


def test_mastery_requires_two_passes():
    state = ensure_prisms({"store": {"store_id": "t"}})
    report = {
        "probe": "literacy-corpus-quiz",
        "total": 2,
        "know": 2,
        "empty": 0,
        "wrong": 0,
    }
    r1 = promote_from_probe_report(state, report, tick=1)
    assert r1.passed
    promote_from_probe_report(state, report, tick=2)
    r2 = promote_routes_from_probe_report(state, report, min_mastery_streak=2)
    assert r2.promoted


def test_record_gate_attempt():
    state: dict = {}
    record_gate_attempt(state, "probe:x", passed=True, tick=1)
    assert not mastery_ready(state, "probe:x", min_streak=2)
    record_gate_attempt(state, "probe:x", passed=True, tick=2)
    assert mastery_ready(state, "probe:x", min_streak=2)
