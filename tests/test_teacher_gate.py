#!/usr/bin/env python3
"""Teacher gate registry — agent KSA vs sidecar spec regression."""

from __future__ import annotations

from casa.domain.emergent_promote import record_probe_gate
from casa.domain.mastery_gate import mastery_ready, mastery_status
from casa.domain.teacher_gate import (
    GateKind,
    gate_kind_for_probe,
    probe_gate_passed,
)
from casa.prisms.memory.memory_prisms import ensure_prisms


def test_gate_kind_registry():
    assert gate_kind_for_probe("literacy-corpus-quiz") is GateKind.AGENT_KSA
    assert gate_kind_for_probe("possessive-pilot") is GateKind.SIDECAR_SPEC
    assert gate_kind_for_probe("numeral-rule") is GateKind.SIDECAR_SPEC


def test_phrase_know_alone_does_not_pass_unknown_honest_probe():
    report = {"probe": "unknown-probe", "phrase_know": True}
    assert gate_kind_for_probe("unknown-probe", report) is GateKind.SIDECAR_SPEC
    assert probe_gate_passed(report)


def test_sidecar_pass_does_not_credit_mastery():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0, "store": {"store_id": "t"}})
    report = {"probe": "possessive-pilot", "pass": True, "total": 3, "know": 3}
    r1 = record_probe_gate(state, report, tick=1)
    r2 = record_probe_gate(state, report, tick=2)
    assert r1.passed and r2.passed
    assert "sidecar_no_mastery_credit" in r1.skipped
    assert not mastery_ready(state, "possessive-pilot")
    assert mastery_status(state, "possessive-pilot")["streak"] == 0


def test_agent_ksa_still_credits_mastery():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0, "store": {"store_id": "t"}})
    report = {
        "probe": "literacy-corpus-quiz",
        "store_id": "t",
        "total": 4,
        "know": 4,
        "empty": 0,
        "wrong": 0,
    }
    record_probe_gate(state, report, tick=1)
    record_probe_gate(state, report, tick=2)
    assert mastery_ready(state, "literacy-corpus-quiz")


def test_phrase_compose_requires_word_reads():
    report = {
        "probe": "phrase-compose-pilot",
        "phrase_know": True,
        "know_words": 1,
        "total_words": 3,
    }
    assert not probe_gate_passed(report)
    report["know_words"] = 3
    assert probe_gate_passed(report)
