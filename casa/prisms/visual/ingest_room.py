#!/usr/bin/env python3
"""Ingest room (or any) RGB frames into von-neumann visual tract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.domain.prism_ids import PRISM_VISUAL
from casa.domain.prism_wire import prism_block
from casa.domain.visual_tract import VISUAL_LATTICE_IDS
from casa.prisms.memory.memory_prisms import ensure_prisms, run_sleep
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state
from casa.prisms.visual.bootstrap import ensure_prism_visual
from casa.prisms.visual.imprint import imprint_visual_frame
from casa.sensory.load_rgb_frame import load_rgb_frame


def _token_counts(state: dict) -> dict[str, int]:
    lats = prism_block(state, PRISM_VISUAL).get("lattices") or {}
    out: dict[str, int] = {}
    for lid in VISUAL_LATTICE_IDS:
        cells = (lats.get(lid) or {}).get("cells") or []
        out[lid] = sum(len(c) for c in cells)
    return out


def ingest_room_frames(
    store_dir: Path,
    image_paths: list[Path],
    *,
    scene_label: str = "room",
    sleep_after_each: bool = True,
    persist: bool = True,
) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    paths = [p.resolve() for p in image_paths if p.is_file()]
    if not paths:
        raise ValueError("no image files to ingest")

    boot = boot_store(store_dir, prefer_field_state=True)
    state = ensure_prisms(boot["state"])
    state.setdefault("store", {})["store_id"] = store_dir.name
    state["store"]["last_class"] = "visual-room"

    ensure_prism_visual(state)
    frames_report: list[dict[str, Any]] = []
    sleep_reports: list[dict[str, Any]] = []

    for path in paths:
        frame = load_rgb_frame(path)
        rep = imprint_visual_frame(
            state,
            frame,
            frame_id=path.stem,
            scene_label=scene_label,
            record_episode=True,
        )
        sleep_rep = None
        if sleep_after_each and rep.get("episode_id"):
            sleep_rep = run_sleep(state, None)
            sleep_reports.append(sleep_rep)
        frames_report.append({"path": str(path), **rep})

    token_counts = _token_counts(state)
    ready = all(token_counts.get(lid, 0) > 0 for lid in VISUAL_LATTICE_IDS)

    if persist:
        mark_runtime_dirty(state)
        save_runtime_state(store_dir, state, force=True)

    return {
        "store_id": store_dir.name,
        "frames": len(frames_report),
        "frames_report": frames_report,
        "token_counts": token_counts,
        "s2a_ready": ready,
        "sleep_runs": len(sleep_reports),
    }
