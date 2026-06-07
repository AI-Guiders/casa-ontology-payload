#!/usr/bin/env python3
"""Working Memory Prism — ADR-0055."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.memory.memory_prisms import ensure_prisms, hippo_episodes
from casa.prisms.memory.wm import (
    DEFAULT_SCRATCH_LATTICE,
    place_wm_edge,
    place_wm_node,
    promote_wm_edge,
    prune_wm_lattice,
    score_wm_edges,
    spawn_wm_lattice,
    wm_after_partner_turn,
    wm_bind_focus_concepts,
    wm_blocks_for_bind,
    wm_on_sleep_boundary,
    wm_tract_boosts,
)
from casa.prisms.tick.tract import compete_tract_intent


def _state() -> dict:
    return ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 1})


def test_spawn_scratch_lattice() -> None:
    state = _state()
    lid = spawn_wm_lattice(state, tick=1, topic_slug="scratch")
    assert lid == DEFAULT_SCRATCH_LATTICE
    assert lid in state["prisms"]["prism_agent"]["lattices"]


def test_place_node_and_edge() -> None:
    state = _state()
    spawn_wm_lattice(state, tick=1)
    a = place_wm_node(state, "ru.prop.rain", tick=1, modality="text")
    b = place_wm_node(state, "ru.prop.cancel", tick=1, modality="dialogue")
    edge = place_wm_edge(state, "ru.prop.rain", "ru.prop.cancel", tick=2, modality="dialogue")
    assert a["node_id"].startswith("agent.wm.node.")
    assert b["lattice_id"] == DEFAULT_SCRATCH_LATTICE
    assert edge and edge["edge_id"].startswith("agent.wm.edge.")


def test_score_reuse_and_anti_paste() -> None:
    state = _state()
    spawn_wm_lattice(state, tick=1)
    row = place_wm_edge(state, "math.entity.stick", "math.role.heap", tick=1)
    assert row
    eid = str(row["edge_id"])
    score_wm_edges(state, tick=2, turn_paste=0.1, edge_ids=[eid])
    low = score_wm_edges(state, tick=2, turn_paste=0.9, edge_ids=[eid])[eid]
    place_wm_edge(state, "math.entity.stick", "math.role.heap", tick=5)
    high = score_wm_edges(state, tick=5, turn_paste=0.1, edge_ids=[eid])[eid]
    assert high > low


def test_cross_cue_modalities() -> None:
    state = _state()
    spawn_wm_lattice(state, tick=1)
    place_wm_node(state, "passage.sent.0", tick=1, modality="text")
    place_wm_node(state, "ru.dialog.partner_recent", tick=2, modality="dialogue")
    edge = place_wm_edge(state, "passage.sent.0", "ru.dialog.partner_recent", tick=2)
    assert edge
    meta = state["prisms"]["prism_agent"]["wm_lattices"][DEFAULT_SCRATCH_LATTICE]
    edge_row = meta["edges"][edge["edge_id"]]
    assert len(edge_row["modalities"]) >= 2
    place_wm_edge(state, "passage.sent.0", "ru.dialog.partner_recent", tick=4)
    sigma = score_wm_edges(state, tick=4, edge_ids=[edge["edge_id"]])[edge["edge_id"]]
    assert sigma >= 0.55


def test_partner_callback_boosts_blocks() -> None:
    state = _state()
    spawn_wm_lattice(state, tick=1)
    place_wm_edge(state, "lang.word.парк", "lang.word.дождь", tick=1)
    blocks = wm_blocks_for_bind(state, "Как мы говорили про парк?", k=2)
    assert blocks
    assert blocks[0]["source"] == "wm_prism"


def test_wm_tract_boost() -> None:
    state = _state()
    spawn_wm_lattice(state, tick=1)
    edge = place_wm_edge(state, "ru.prop.stance", "ru.prop.reason", tick=1)
    assert edge
    meta = state["prisms"]["prism_agent"]["wm_lattices"][DEFAULT_SCRATCH_LATTICE]
    for tick in (2, 3, 4):
        score_wm_edges(state, tick=tick, query="Продолжим — какая связь между позицией и причиной?")
    meta["edges"][edge["edge_id"]]["score"] = 0.72
    boosts = wm_tract_boosts(state, "Продолжим — какая связь между позицией и причиной?")
    assert boosts.get("discuss", 0) > 0


def test_compete_tract_with_wm_state() -> None:
    state = _state()
    spawn_wm_lattice(state, tick=1)
    place_wm_edge(state, "ru.prop.stance", "ru.prop.reason", tick=1)
    for _ in range(3):
        score_wm_edges(state, tick=2, query="Как мы говорили про связь?")
    q = "Как мы говорили про связь между позицией и причиной?"
    _, ranked_plain = compete_tract_intent(q, None)
    _, ranked_wm = compete_tract_intent(q, None, state=state)
    plain_discuss = next(t for t in ranked_plain if t.tract_id == "discuss").score
    wm_discuss = next(t for t in ranked_wm if t.tract_id == "discuss").score
    assert wm_discuss >= plain_discuss


def test_prune_removes_decayed_edges() -> None:
    state = _state()
    spawn_wm_lattice(state, tick=1)
    edge = place_wm_edge(state, "agent.world.idea.a", "agent.world.idea.b", tick=1)
    assert edge
    meta = state["prisms"]["prism_agent"]["wm_lattices"][DEFAULT_SCRATCH_LATTICE]
    meta["edges"][edge["edge_id"]]["score"] = 0.05
    rep = prune_wm_lattice(state, tick=8)
    assert edge["edge_id"] in rep["removed"]


def test_sleep_boundary_creates_hippo_episode_not_world() -> None:
    state = _state()
    spawn_wm_lattice(state, tick=1)
    edge = place_wm_edge(state, "math.entity.stick", "math.role.heap", tick=1)
    assert edge
    meta = state["prisms"]["prism_agent"]["wm_lattices"][DEFAULT_SCRATCH_LATTICE]
    meta["edges"][edge["edge_id"]]["score"] = 0.55
    meta["edges"][edge["edge_id"]]["tier"] = "episode_candidate"
    before = len(hippo_episodes(state))
    rep = wm_on_sleep_boundary(state)
    after = len(hippo_episodes(state))
    assert after >= before
    assert rep["hippo_episodes"] or rep["episode_candidates"]


def test_promote_wm_edge_requires_theta() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="casa-wm-"))
    try:
        (tmp / "store_profile.json").write_text(json.dumps({"subject_mode": True}) + "\n", encoding="utf-8")
        state = _state()
        spawn_wm_lattice(state, tick=1)
        edge = place_wm_edge(state, "math.num.five", "math.num.two", tick=1)
        assert edge
        meta = state["prisms"]["prism_agent"]["wm_lattices"][DEFAULT_SCRATCH_LATTICE]
        meta["edges"][edge["edge_id"]]["score"] = 0.70
        out = promote_wm_edge(tmp, state, edge["edge_id"], persist=False)
        assert out["promoted"].startswith("agent.world.relation.")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_wm_after_partner_turn_persists_scores() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="casa-wm-turn-"))
    try:
        (tmp / "store_profile.json").write_text(json.dumps({"subject_mode": True}) + "\n", encoding="utf-8")
        state = _state()
        wm_obj = WorkingMemory(tick=8, user_query="связь")
        bind = wm_bind_focus_concepts(
            state,
            ["ru.prop.rain", "ru.prop.cancel"],
            tick=8,
        )

        class _Ctx:
            blocks = [{"concept_id": "ru.prop.rain", "text": "дождь"}]
            wm = wm_obj
            wm_bind = bind

        rep = wm_after_partner_turn(
            state,
            tmp,
            _Ctx(),
            "Связь: дождь отменил прогулку.",
            tick=8,
            persist=False,
        )
        assert rep["wm_edge_scores"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_overload_freezes_spawn() -> None:
    state = _state()
    rep = wm_bind_focus_concepts(
        state,
        ["ru.prop.a", "ru.prop.b"],
        tick=1,
        overloaded=True,
    )
    assert rep.get("skipped") == "overload_freeze"
