#!/usr/bin/env python3
"""ADR-0018 v0: prism_visual ingest + predict vis."""

from __future__ import annotations

from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.memory.prism_router import resolve_route, RouteContext
from casa.prisms.memory.prism_spawn import ensure_vision_bootstrap, list_content_prism_ids, spawn_prism
from casa.prisms.shared.prism_state import PRISM_KIND_CONTROL, PRISM_VISUAL
from casa.prisms.tick.predictor import predict
from casa.prisms.visual.ingest_vis import ingest_vis_claim


def test_vision_ingest_and_predict():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    ensure_vision_bootstrap(state)
    assert PRISM_VISUAL in list_content_prism_ids(state)
    ingest_vis_claim(
        state,
        {
            "concept_id": "vis.animal.cow",
            "image_ref": "lab/bukvar_vis/cow.png",
            "links": ["корова"],
        },
    )
    assert state["vis_refs"]["lab/bukvar_vis/cow.png"] == "vis.animal.cow"
    pred = predict(state, "vis.animal.cow", modality="vis")
    assert pred["hypothesis"] == "vis.animal.cow"
    route = resolve_route(state, RouteContext(modality="vis"))
    assert route.prism_id == PRISM_VISUAL


def test_spawn_control_vis_prism():
    state = ensure_prisms({"schema_version": "multi_prism_v1", "field_version": 0})
    rep = spawn_prism(state, "prism_control_vis", kind="control")
    assert rep["kind"] == "control"
    from casa.prisms.shared.prism_state import prism_block

    lats = prism_block(state, "prism_control_vis").get("lattices") or {}
    assert "lattice_vis_sn" in lats or "control-vis-salience" in lats
