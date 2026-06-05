#!/usr/bin/env python3
"""Kolb relink tick — proposal + life hook policy."""

from __future__ import annotations

import json
from pathlib import Path

from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.tick import ControlExtensions
from casa.prisms.tick.kolb_relink_tick import (
    agent_wants_kolb,
    maybe_kolb_relink_tick,
    propose_vis_lex_relink,
)
from casa.prisms.memory.lexical_lattice_bootstrap import ensure_lexical_lattices
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.f0_stack import strengthen_graph_edge, graph_edge_token
from casa.prisms.memory.memory_prisms import memory_lattices, persist_content_lattices
from casa.prisms.shared.lattice_names_v1 import LEXICON_RU
from casa.prisms.visual.bridge_math import vis_frame_concept_id


def test_propose_from_predict_mismatch():
    wm = WorkingMemory(step_focus="word-abc-sans")
    control = ControlExtensions(
        predicted=("lang.word.old",),
        surprise=("lang.word.new",),
        prediction_error=0.5,
        dan_mask=(),
        sparse_ratio=0.0,
        masked_digest=(),
        value=0.6,
    )
    ep = {
        "structure_tag": "predict_mismatch",
        "surface_attempt": "lang.word.old",
        "correct": "lang.word.new",
        "concept_id": vis_frame_concept_id("word-abc-sans"),
    }
    prop = propose_vis_lex_relink(wm=wm, control=control, hippo_ep=ep)
    assert prop is not None
    assert prop.frame_id == "word-abc-sans"
    assert prop.old_lex == "lang.word.old"
    assert prop.new_lex == "lang.word.new"


def test_agent_wants_kolb_reads_session(tmp_path: Path):
    (tmp_path / "agent_session.json").write_text(
        json.dumps({"self_drive": {"want_kolb": True}}, ensure_ascii=False),
        encoding="utf-8",
    )
    assert agent_wants_kolb(tmp_path)


def test_maybe_kolb_relink_skips_without_self_verify():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    ensure_lexical_lattices(state)
    wm = WorkingMemory(step_focus="word-x-sans")
    control = ControlExtensions(
        predicted=("lang.word.a",),
        surprise=("lang.word.b",),
        prediction_error=0.8,
        dan_mask=(),
        sparse_ratio=0.0,
        masked_digest=(),
        value=0.9,
    )
    ep = {
        "structure_tag": "predict_mismatch",
        "surface_attempt": "lang.word.a",
        "correct": "lang.word.b",
    }
    rep = maybe_kolb_relink_tick(
        Path("/nonexistent"),
        state,
        wm=wm,
        control=control,
        hippo_ep=ep,
        min_surprise_value=0.4,
    )
    assert rep is not None
    assert rep.get("skipped") is True


def test_maybe_kolb_relink_applies_when_lex_leaders_confirm(tmp_path: Path):
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    ensure_lexical_lattices(state)
    frame = "word-fix-sans"
    vis_cid = vis_frame_concept_id(frame)
    lats = memory_lattices(state)
    strengthen_graph_edge(lats, LEXICON_RU, vis_cid, "co_occurs", "lang.word.old", copies=4)
    strengthen_graph_edge(lats, LEXICON_RU, vis_cid, "co_occurs", "lang.word.new", copies=6)
    persist_content_lattices(state, lats)

    from casa.prisms.visual.bridge_lex import reinforce_vis_lex_bridge

    reinforce_vis_lex_bridge(
        state,
        frame_id=frame,
        lex_cid="lang.word.new",
        copies=10,
        provenance="test_setup",
    )

    wm = WorkingMemory(step_focus=frame)
    control = ControlExtensions(
        predicted=("lang.word.old",),
        surprise=("lang.word.new",),
        prediction_error=0.7,
        dan_mask=(),
        sparse_ratio=0.0,
        masked_digest=(),
        value=0.7,
    )
    ep = {
        "structure_tag": "predict_mismatch",
        "surface_attempt": "lang.word.old",
        "correct": "lang.word.new",
        "concept_id": vis_cid,
    }
    rep = maybe_kolb_relink_tick(
        tmp_path,
        state,
        wm=wm,
        control=control,
        hippo_ep=ep,
        min_surprise_value=0.4,
    )
    assert rep is not None
    assert not rep.get("skipped")
    assert rep.get("minted")
    tok_old = graph_edge_token(vis_cid, "co_occurs", "lang.word.old")
    tok_new = graph_edge_token(vis_cid, "denotes", "lang.word.new")
    cells = memory_lattices(state)[LEXICON_RU]["cells"]
    assert sum(tok_old in c for c in cells if isinstance(c, list)) == 0
    assert sum(tok_new in c for c in cells if isinstance(c, list)) >= 1
