#!/usr/bin/env python3
"""Agent self-drive: knowledge seek + skill promote on tick."""

from __future__ import annotations

import json
from pathlib import Path

from casa.domain.plan_tick import PlanTick
from casa.domain.routing import ROUTE_KIND_CAPABILITY, Router
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.tick import ControlExtensions
from casa.prisms.memory.lexical_lattice_bootstrap import ensure_lexical_lattices
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.f0_stack import strengthen_graph_edge
from casa.prisms.memory.memory_prisms import memory_lattices, persist_content_lattices
from casa.prisms.shared.lattice_names_v1 import LEXICON_RU
from casa.prisms.tick.agent_self_drive_tick import (
    agent_active_intent,
    maybe_agent_self_drive_tick,
    maybe_promote_skill_on_verify,
    prepare_phrase_agent_tick,
    seek_agent_knowledge,
)
from casa.prisms.visual.bridge_math import vis_frame_concept_id
from casa.prisms.visual.bridge_lex import reinforce_vis_lex_bridge


def _control(value: float = 0.5) -> ControlExtensions:
    return ControlExtensions(
        predicted=(),
        surprise=(),
        prediction_error=0.0,
        dan_mask=(),
        sparse_ratio=0.0,
        masked_digest=(),
        value=value,
    )


def test_agent_active_intent_with_goal():
    wm = WorkingMemory(goal_id="goal.read.word")
    assert agent_active_intent(wm, Path("/x"))


def test_seek_agent_knowledge_writes_sn():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    wm = WorkingMemory(goal_id="goal.read.word", step_capability="skill.read.analytic", step_focus="word-x-sans")
    mem_prep = {
        "plan_tick": wm.to_dict(),
        "route": type("R", (), {"prism_id": "prism_visual"})(),
        "routing_chain": None,
    }
    out = seek_agent_knowledge(state, wm=wm, mem_prep=mem_prep, cue="")
    assert out["modality"] == "vis"
    assert state["sn"].get("agent_knowledge_seek") is not None


def test_skill_promote_after_lex_verify(tmp_path: Path):
    state = ensure_prisms(
        {"schema_version": "multi_prism_v1", "field_version": 0, "store": {"store_id": "t"}}
    )
    ensure_lexical_lattices(state)
    frame = "word-skill-sans"
    vis_cid = vis_frame_concept_id(frame)
    lats = memory_lattices(state)
    strengthen_graph_edge(lats, LEXICON_RU, vis_cid, "co_occurs", "lang.word.skill", copies=5)
    persist_content_lattices(state, lats)
    reinforce_vis_lex_bridge(state, frame_id=frame, lex_cid="lang.word.skill", copies=8)

    wm = WorkingMemory(
        goal_id="goal.read.word",
        active_plan_id="plan.trial.analytic_read",
        plan_steps=["skill.read.analytic", "skill.verify.lex"],
        step_index=0,
        step_capability="skill.read.analytic",
        step_focus=frame,
    )
    mem_prep = {"plan_tick": wm.to_dict(), "routing_chain": None}
    knowledge = {
        "predict_verdict": "pass",
        "hypothesis": "lang.word.skill",
        "modality": "vis",
    }
    maybe_promote_skill_on_verify(state, wm=wm, mem_prep=mem_prep, knowledge=knowledge)
    rep = maybe_promote_skill_on_verify(
        state,
        wm=wm,
        mem_prep=mem_prep,
        knowledge=knowledge,
    )
    assert rep is not None
    assert not rep.get("skipped")
    caps = Router.bind(state).routes(route_kind=ROUTE_KIND_CAPABILITY)
    assert any(r.target_skill == "skill.read.analytic" for r in caps)


def test_phrase_compose_slots_verify_on_probe_mastery():
    state = ensure_prisms(
        {"schema_version": "multi_prism_v1", "field_version": 0, "store": {"store_id": "t"}}
    )
    from casa.domain.emergent_promote import promote_from_probe_report

    report = {
        "probe": "phrase-agent-store",
        "phrase_know": True,
        "verdict": "phrase_know",
        "total_words": 3,
        "know_words": 3,
        "events": [{"phrase_know": True, "total_words": 3, "know_words": 3}],
    }
    promote_from_probe_report(state, report, tick=1)
    promote_from_probe_report(state, report, tick=2)

    wm = WorkingMemory(
        goal_id="goal.read.phrase",
        active_plan_id="plan.trial.phrase_compose",
        plan_steps=["skill.read.analytic", "skill.compose.slots", "skill.verify.phrase"],
        step_index=1,
        step_capability="skill.compose.slots",
    )
    mem_prep = {"plan_tick": wm.to_dict(), "routing_chain": None}
    knowledge = {"predict_verdict": "pass", "hypothesis": "lang.event.transitive.wash.v0"}
    rep = maybe_promote_skill_on_verify(state, wm=wm, mem_prep=mem_prep, knowledge=knowledge)
    assert rep is not None
    assert not rep.get("skipped")


def test_self_drive_prepares_phrase_plan():
    state = ensure_prisms(
        {"schema_version": "multi_prism_v1", "field_version": 0, "store": {"store_id": "t"}}
    )
    from casa.domain.emergent_promote import promote_from_probe_report, promote_routes_from_probe_report

    for report in (
        {"probe": "analytic-read-corpus-r1", "items": [{"verdict": "analytic_know"}]},
        {
            "probe": "phrase-agent-store",
            "phrase_know": True,
            "verdict": "phrase_know",
            "total_words": 3,
            "know_words": 3,
            "events": [{"phrase_know": True, "total_words": 3, "know_words": 3}],
        },
    ):
        promote_from_probe_report(state, report, tick=1)
        promote_from_probe_report(state, report, tick=2)
        promote_routes_from_probe_report(state, report, min_mastery_streak=2)

    wm = WorkingMemory(goal_id="goal.read.phrase#lang.event.transitive.wash.v0")
    mem_prep: dict = {"plan_tick": {}, "routing_chain": None}
    plan = prepare_phrase_agent_tick(state, wm, mem_prep)
    assert plan.plan_steps
    assert wm.step_focus


def test_maybe_agent_self_drive_with_want_kolb(tmp_path: Path):
    (tmp_path / "agent_session.json").write_text(
        json.dumps({"self_drive": {"want_kolb": True}}, ensure_ascii=False),
        encoding="utf-8",
    )
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    wm = WorkingMemory(goal_id="goal.learn.corpus")
    mem_prep = {
        "plan_tick": PlanTick(goal_id="goal.learn.corpus").to_dict(),
        "route": type("R", (), {"prism_id": "prism_visual"})(),
        "routing_chain": None,
    }
    rep = maybe_agent_self_drive_tick(
        tmp_path,
        state,
        wm=wm,
        control=_control(0.1),
        mem_prep=mem_prep,
    )
    assert rep is not None
    assert rep.get("agent_controlled")
    assert rep.get("knowledge_seek")
