"""Emergent vis↔lex bridges — scene-scoped co-occurrence (no Cartesian batch)."""

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
from casa.prisms.shared.lattice_names_v1 import LEXICON_RU
from casa.prisms.visual.bootstrap import ensure_prism_visual
from casa.prisms.visual.bridge_lex import bridge_exists_on_field, vis_frame_concept_id
from casa.prisms.visual.imprint import imprint_visual_frame
from casa.sensory.load_rgb_frame import load_rgb_frame
from casa.sensory.sample_ppm import write_synthetic_room_ppm


def _seed_lex_concept(state: dict, concept_id: str, *, copies: int = 6) -> None:
    lats = memory_lattices(state)
    lat = lats.setdefault(
        LEXICON_RU,
        {"width": 32, "height": 32, "cells": [[] for _ in range(32 * 32)]},
    )
    g = Grid(width=32, height=32, cells=[list(c) for c in lat["cells"]])
    from casa.prisms.memory.stack import _place_token

    g = _place_token(g, f"C:{concept_id}", f"C:{concept_id}", copies=copies, radius=4)
    lat["cells"] = g.cells
    persist_content_lattices(state, {LEXICON_RU: lat})


def test_sleep_cooccurrence_lex_same_scene(tmp_path) -> None:
    ppm = tmp_path / "card.ppm"
    write_synthetic_room_ppm(ppm, width=64, height=48)
    frame = load_rgb_frame(ppm)
    state = ensure_prisms({})
    ensure_prism_visual(state)
    _seed_lex_concept(state, "lang.word.alpha")

    scene = "moment:test:p0"
    append_episode(
        state,
        cue="alpha",
        surface_attempt="альфа",
        correct="альфа",
        lattice_id=LEXICON_RU,
        concept_id="lang.word.alpha",
        scene=scene,
        episode_source="ingest",
    )
    rep = imprint_visual_frame(
        state,
        frame,
        frame_id="word-alpha-sans",
        scene_label="card:word:alpha",
    )
    assert rep.get("episode_id")
    vis_cid = vis_frame_concept_id("word-alpha-sans")
    assert not bridge_exists_on_field(
        memory_lattices(state),
        src=vis_cid,
        relation="co_occurs",
        dst="lang.word.alpha",
    )

    sleep_rep = run_sleep(state, None)
    kinds = [x.get("kind") for x in sleep_rep.get("items") or []]
    assert "emergent_crosslink_lex" in kinds
    assert bridge_exists_on_field(
        memory_lattices(state),
        src=vis_cid,
        relation="co_occurs",
        dst="lang.word.alpha",
    )


def test_sleep_cooccurrence_lex_no_cross_scene(tmp_path) -> None:
    ppm_a = tmp_path / "a.ppm"
    ppm_b = tmp_path / "b.ppm"
    write_synthetic_room_ppm(ppm_a, width=64, height=48)
    write_synthetic_room_ppm(ppm_b, width=64, height=48)
    state = ensure_prisms({})
    ensure_prism_visual(state)
    _seed_lex_concept(state, "lang.word.alpha")
    _seed_lex_concept(state, "lang.word.beta")

    append_episode(
        state,
        cue="alpha",
        surface_attempt="альфа",
        correct="альфа",
        lattice_id=LEXICON_RU,
        concept_id="lang.word.alpha",
        scene="moment:test:p0",
        episode_source="ingest",
    )
    append_episode(
        state,
        cue="beta",
        surface_attempt="бета",
        correct="бета",
        lattice_id=LEXICON_RU,
        concept_id="lang.word.beta",
        scene="moment:test:p1",
        episode_source="ingest",
    )
    imprint_visual_frame(
        state,
        load_rgb_frame(ppm_b),
        frame_id="word-beta-sans",
        scene_label="card:word:beta",
    )
    vis_b = vis_frame_concept_id("word-beta-sans")

    run_sleep(state, None)

    assert not bridge_exists_on_field(
        memory_lattices(state),
        src=vis_b,
        relation="co_occurs",
        dst="lang.word.alpha",
    )
    assert bridge_exists_on_field(
        memory_lattices(state),
        src=vis_b,
        relation="co_occurs",
        dst="lang.word.beta",
    )
