#!/usr/bin/env python3
"""Phrase compose P1 — slot bind and agreement (ADR-0033)."""

from __future__ import annotations

from casa.domain.emergent_promote import promote_from_probe_report, promote_routes_from_probe_report
from casa.domain.routing import ROUTE_KIND_APPLICABILITY, ROUTE_KIND_CAPABILITY, Router
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.visual.phrase_compose import bind_slots, check_agreement, compose_phrase_verdict


def _pilot_entry() -> dict:
    return {
        "event_id": "lang.event.transitive.wash.v0",
        "words": [
            {"role": "agent", "surface": "мама", "slug": "d2a8dc30e406"},
            {"role": "verb", "surface": "мыла", "slug": "27dae5010f7e"},
            {"role": "patient", "surface": "раму", "slug": "c6eebd8384e6"},
        ],
        "agreement": [{"agent": "мама", "verb": "мыла", "kind": "subjectVerb.fem.sg.past"}],
    }


def _word_read(surface: str, *, verdict: str = "analytic_know") -> dict:
    return {
        "surface": surface,
        "word_concept_id": f"lang.word.{surface}",
        "verdict": verdict,
        "via": "novel_compose",
    }


def test_bind_slots_and_agreement_ok():
    entry = _pilot_entry()
    reads = [_word_read("мама"), _word_read("мыла"), _word_read("раму")]
    bind = bind_slots(reads, entry["words"])
    assert bind["complete"]
    agr = check_agreement(bind["slots"], entry["agreement"])
    assert agr["ok"]


def test_compose_phrase_know():
    entry = _pilot_entry()
    reads = [_word_read("мама"), _word_read("мыла"), _word_read("раму")]
    out = compose_phrase_verdict(reads, entry)
    assert out["phrase_know"]
    assert out["verdict"] == "phrase_know"


def test_compose_word_fail():
    entry = _pilot_entry()
    reads = [_word_read("мама"), _word_read("мыла", verdict="word_not_in_ltm"), _word_read("раму")]
    out = compose_phrase_verdict(reads, entry)
    assert not out["phrase_know"]
    assert out["verdict"] == "word_fail"


def test_promote_phrase_compose_gate():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0, "store": {"store_id": "von-neumann"}})
    report = {
        "probe": "phrase-compose-pilot",
        "phrase_know": True,
        "verdict": "phrase_know",
        "total_words": 3,
        "know_words": 3,
    }
    first = promote_from_probe_report(state, report, tick=1)
    assert first.passed
    pending = promote_routes_from_probe_report(state, report, min_mastery_streak=2)
    assert pending.skipped and "mastery_pending" in pending.skipped[0]
    promote_from_probe_report(state, report, tick=2)
    second = promote_routes_from_probe_report(state, report, min_mastery_streak=2)
    assert second.promoted
    router = Router.bind(state)
    caps = router.routes(route_kind=ROUTE_KIND_CAPABILITY)
    apps = router.routes(route_kind=ROUTE_KIND_APPLICABILITY)
    assert any(r.target_skill == "skill.read.phrase" for r in caps)
    assert any(r.target_plan.startswith("plan.phrase_compose_") for r in apps)
