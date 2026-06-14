"""Lesson moment — visual + math in one sleep batch."""

from __future__ import annotations

import pytest

from pathlib import Path

from casa.cli.ingest_lesson_moment import ingest_lesson_moment
from casa.domain.visual_tract import LATTICE_V1_LUM
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.shared.lattice_names_v1 import SCHEMA_MATH
from casa.prisms.visual.bootstrap import ensure_prism_visual
from casa.prisms.visual.bridge_math import bridge_exists_on_field, vis_frame_concept_id
from casa.prisms.visual.imprint import imprint_visual_frame
from casa.sensory.load_rgb_frame import load_rgb_frame
from casa.sensory.sample_ppm import write_synthetic_room_ppm


def test_lesson_moment_cooccurrence(tmp_path: Path) -> None:
    pytest.importorskip("PIL", reason="lesson-moment visual ingest requires Pillow")
    ppm = tmp_path / "card.ppm"
    write_synthetic_room_ppm(ppm, width=64, height=48)
    frame = load_rgb_frame(ppm)

    class_dir = tmp_path / "class"
    images = class_dir / "lesson/images"
    images.mkdir(parents=True)
    img = images / "card.jpg"
    img.write_bytes(ppm.read_bytes())

    manifest = {
        "class_id": "test-visual",
        "stages": [{"id": "stage-1", "order": 1, "lesson_ids": ["lesson-1"]}],
        "frames": [
            {
                "id": "test-card",
                "path": "lesson/images/card.jpg",
                "scene_label": "card:test",
                "lesson_id": "lesson-1",
            }
        ],
    }
    (class_dir / "class.manifest.json").write_text(
        __import__("json").dumps(manifest),
        encoding="utf-8",
    )

    store_dir = tmp_path / "store"
    store_dir.mkdir()
    (store_dir / "ltm").mkdir()
    (store_dir / "ltm" / "pack.manifest.json").write_text('{"nca":{}}', encoding="utf-8")

    state = ensure_prisms({})
    ensure_prism_visual(state)

    rep = ingest_lesson_moment(
        store_dir,
        class_dir,
        moment_id="test-moment",
        stage_ids=["stage-1"],
        math_episodes=[
            {"cue": "2+3", "correct": "5", "concept_id": "math.op.add"},
        ],
        interleave="after_each_visual",
        sleep=True,
        persist=False,
        state=state,
    )

    assert rep["visual_episodes"] == 1
    assert rep["math_episodes"] == 1
    assert rep["bridges_emergent"] >= 1

    vis_cid = vis_frame_concept_id("test-card")
    assert bridge_exists_on_field(
        memory_lattices(state),
        src=vis_cid,
        relation="co_occurs",
        dst="math.op.add",
    )
