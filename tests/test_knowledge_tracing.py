#!/usr/bin/env python3
from __future__ import annotations

from casa.domain.knowledge_tracing import interval_from_p_known, p_known, record_trace_attempt


def test_p_known_increases_on_success():
    state: dict = {}
    record_trace_attempt(state, "syllable.ла", passed=False, tick=1)
    row = record_trace_attempt(state, "syllable.ла", passed=True, tick=2)
    assert p_known(row) > 0.3
    assert interval_from_p_known(p_known(row)) >= 3
