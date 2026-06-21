"""Emergent cross-prism bridges — co-occurrence and agent self_promote."""

from __future__ import annotations

from casa.domain.visual_tract import LATTICE_V1_LUM
from casa.prisms.memory.memory_prisms import (
    append_episode,
    ensure_prisms,
    memory_lattices,
    persist_content_lattices,
    run_sleep,
)
from casa.prisms.shared.codec_grid import Grid
from casa.prisms.shared.lattice_names_v1 import SCHEMA_MATH
from casa.prisms.visual.bootstrap import ensure_prism_visual
from casa.prisms.visual.bridge_math import (
    agent_promote_crosslink,
    bridge_exists_on_field,
    extract_emergent_vis_math_bridges,
    self_promote_vis_math_bridge,
    vis_frame_concept_id,
)
from casa.prisms.visual.imprint import imprint_visual_frame
from casa.sensory.load_rgb_frame import load_rgb_frame
from casa.sensory.sample_ppm import write_synthetic_room_ppm


def _seed_math_concept(state: dict, concept_id: str, *, copies: int = 6) -> None:
    lats = memory_lattices(state)
    lat = lats.setdefault(
        SCHEMA_MATH,
        {"width": 32, "height": 32, "cells": [[] for _ in range(32 * 32)]},
    )
    g = Grid(width=32, height=32, cells=[list(c) for c in lat["cells"]])
    from casa.prisms.memory.stack import _place_token

    g = _place_token(g, f"C:{concept_id}", f"C:{concept_id}", copies=copies, radius=4)
    lat["cells"] = g.cells
    # seeding schema-math (immutable) is bootstrap-like; the default "hot" context is gated
    persist_content_lattices(state, {SCHEMA_MATH: lat}, write_context="bootstrap")


def test_sleep_cooccurrence_bridge(tmp_path) -> None:
    ppm = tmp_path / "card.ppm"
    write_synthetic_room_ppm(ppm, width=64, height=48)
    frame = load_rgb_frame(ppm)
    state = ensure_prisms({})
    ensure_prism_visual(state)
    _seed_math_concept(state, "math.num.three")

    append_episode(
        state,
        cue="3",
        surface_attempt="",
        correct="3",
        lattice_id=SCHEMA_MATH,
        concept_id="math.num.three",
        scene="lab:math",
        episode_source="ingest",
        structure_tag="self_promote",  # sanctioned earned-write (gate-authorized in production)
    )
    rep = imprint_visual_frame(
        state,
        frame,
        frame_id="numberline-mark-3",
        scene_label="card:numberline:mark-3",
    )
    assert rep.get("episode_id")
    vis_cid = vis_frame_concept_id("numberline-mark-3")
    assert not bridge_exists_on_field(
        memory_lattices(state),
        src=vis_cid,
        relation="co_occurs",
        dst="math.num.three",
    )

    sleep_rep = run_sleep(state, None)
    kinds = [x.get("kind") for x in sleep_rep.get("items") or []]
    assert "emergent_crosslink" in kinds
    assert bridge_exists_on_field(
        memory_lattices(state),
        src=vis_cid,
        relation="co_occurs",
        dst="math.num.three",
    )


def test_agent_promote_crosslink() -> None:
    state = ensure_prisms({})
    ensure_prism_visual(state)
    _seed_math_concept(state, "math.op.add")
    rep = agent_promote_crosslink(
        state,
        src=vis_frame_concept_id("numberline-add-2plus3"),
        relation="denotes",
        dst="math.op.add",
        cue="vis:numberline-add-2plus3",
    )
    assert rep.get("minted")
    assert bridge_exists_on_field(
        memory_lattices(state),
        src=vis_frame_concept_id("numberline-add-2plus3"),
        relation="denotes",
        dst="math.op.add",
    )


def test_self_promote_vis_math_bridge() -> None:
    state = ensure_prisms({})
    ensure_prism_visual(state)
    _seed_math_concept(state, "math.op.sub")
    minted = self_promote_vis_math_bridge(
        state,
        frame_id="numberline-sub-5minus2",
        math_cid="math.op.sub",
    )
    assert minted
    vis_cid = vis_frame_concept_id("numberline-sub-5minus2")
    assert bridge_exists_on_field(
        memory_lattices(state),
        src=vis_cid,
        relation="denotes",
        dst="math.op.sub",
    )
