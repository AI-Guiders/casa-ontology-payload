"""Retinal LRGB codec + visual imprint (S2a)."""

from __future__ import annotations

from casa.domain.visual_tract import VISUAL_LATTICE_IDS
from casa.prisms.memory.memory_prisms import ensure_prisms
from casa.prisms.visual.bootstrap import ensure_prism_visual
from casa.prisms.visual.imprint import imprint_visual_frame
from casa.sensory.load_rgb_frame import load_rgb_frame
from casa.sensory.sample_ppm import write_synthetic_room_ppm


def test_encode_and_imprint_four_lattices(tmp_path) -> None:
    ppm = tmp_path / "room.ppm"
    write_synthetic_room_ppm(ppm, width=64, height=48)
    frame = load_rgb_frame(ppm)
    state = ensure_prisms({})
    ensure_prism_visual(state)
    rep = imprint_visual_frame(state, frame, frame_id="test-room", record_episode=True)
    assert rep.get("episode_id")
    for lid in VISUAL_LATTICE_IDS:
        assert rep["placements"].get(lid, 0) == 32 * 32


def test_lum_from_rgb_channels() -> None:
    from casa.sensory.codecs.retinal_lrgb import luminance_u8

    assert luminance_u8(255, 255, 255) == 255
    assert luminance_u8(0, 0, 0) == 0
