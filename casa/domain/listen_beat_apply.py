"""Apply human-curated beat timelines (e.g. Qwen) into listen manifests."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from casa.domain.listen_beat_model import (
    BEAT_KIND_MOTION,
    assign_beat_media_paths,
    beat_kind,
    count_expected_frame_files,
    normalize_keyframes,
)
from casa.sensory.chapter_scene_cuts import extract_beat_frame


def load_external_beats(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{path}: expected JSON array of beats")
    beats: list[dict[str, Any]] = []
    for i, row in enumerate(raw):
        if not isinstance(row, dict):
            raise ValueError(f"{path}: beat[{i}] must be an object")
        beats.append(dict(row))
    return beats


def split_long_beats(
    beats: list[dict[str, Any]],
    *,
    max_sec: float = 8.0,
) -> list[dict[str, Any]]:
    """Split paired beats longer than max_sec; motion beats pass through."""
    out: list[dict[str, Any]] = []
    for beat in beats:
        if beat_kind(beat) == BEAT_KIND_MOTION:
            out.append(dict(beat))
            continue
        t0 = float(beat["t0"])
        t1 = float(beat["t1"])
        dur = t1 - t0
        if dur <= max_sec + 1e-6:
            out.append(dict(beat))
            continue
        n_chunks = max(2, int(math.ceil(dur / max_sec)))
        step = dur / n_chunks
        ft_raw = beat.get("frame_t")
        note = str(beat.get("note") or "")
        for i in range(n_chunks):
            ct0 = round(t0 + i * step, 3)
            ct1 = round(t1, 3) if i == n_chunks - 1 else round(t0 + (i + 1) * step, 3)
            chunk = {k: v for k, v in beat.items() if k not in ("id", "t0", "t1", "frame_t", "keyframes")}
            chunk["t0"] = ct0
            chunk["t1"] = ct1
            if ft_raw is not None:
                ftf = float(ft_raw)
                if ct0 <= ftf <= ct1:
                    chunk["frame_t"] = round(ftf, 3)
                else:
                    chunk["frame_t"] = round((ct0 + ct1) / 2, 3)
            if note and n_chunks > 1:
                chunk["note"] = f"{note} ({i + 1}/{n_chunks})"
            out.append(chunk)
    for i, row in enumerate(out):
        row["id"] = f"b{i:03d}"
    return out


def close_timeline_end(
    beats: list[dict[str, Any]],
    chapter_t1: float,
    *,
    tol_sec: float = 0.5,
) -> list[dict[str, Any]]:
    if not beats:
        return beats
    target = round(float(chapter_t1), 3)
    last = beats[-1]
    gap = round(target - float(last["t1"]), 3)
    if abs(gap) <= tol_sec:
        last["t1"] = target
    return beats


def assign_beat_paths(
    beats: list[dict[str, Any]],
    *,
    chapter_index: int,
    slug: str,
) -> list[dict[str, Any]]:
    chapter_dir = f"frames/{int(chapter_index):02d}-{slug}"
    rows: list[dict[str, Any]] = []
    for beat in beats:
        bid = str(beat.get("id") or f"b{len(rows):03d}")
        rows.append(assign_beat_media_paths(beat, chapter_dir=chapter_dir, beat_id=bid))
    return rows


def extract_beat_frames(
    video_path: Path,
    beats: list[dict[str, Any]],
    *,
    chapter_t0: float,
    bundle_dir: Path,
) -> int:
    written = 0
    for beat in beats:
        if beat_kind(beat) == BEAT_KIND_MOTION:
            for kf in normalize_keyframes(beat):
                ref = str(kf.get("path") or "")
                if not ref:
                    continue
                t_abs = float(chapter_t0) + float(kf["frame_t"])
                if extract_beat_frame(video_path, t_abs=t_abs, out_jpg=bundle_dir / ref):
                    written += 1
            continue
        path_ref = str(beat.get("path") or "")
        if not path_ref:
            continue
        ft_rel = beat.get("frame_t")
        if ft_rel is None:
            ft_rel = (float(beat["t0"]) + float(beat["t1"])) / 2
        t_abs = float(chapter_t0) + float(ft_rel)
        if extract_beat_frame(video_path, t_abs=t_abs, out_jpg=bundle_dir / path_ref):
            written += 1
    return written


def chapter_slug(scene: dict[str, Any]) -> str:
    frame = str(scene.get("frame") or "")
    if frame.startswith("frames/"):
        parts = Path(frame).parts
        if len(parts) >= 2:
            dir_name = parts[1]
            if "-" in dir_name:
                return dir_name.split("-", 1)[1]
    title = str(scene.get("chapter_title") or scene.get("caption") or "")
    slug = "".join(
        (ch if ch.isalnum() or ch in "._-" else "_")
        for ch in title.strip().lower()
    ).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    idx = int(scene.get("chapter_index") or 0)
    return (slug[:48] or f"chapter-{idx:02d}")


def apply_external_beats_to_scene(
    scene: dict[str, Any],
    external: list[dict[str, Any]],
    *,
    bundle_dir: Path,
    video_path: Path,
    beat_mode: str = "human_curated",
    beat_source: str = "external",
    max_beat_sec: float = 8.0,
) -> dict[str, Any]:
    chapter_t0 = float(scene.get("t0") or 0.0)
    chapter_t1 = float(scene.get("t1") or chapter_t0 + 1.0)
    slug = chapter_slug(scene)
    idx = int(scene.get("chapter_index") or 0)

    beats = split_long_beats(external, max_sec=max_beat_sec)
    beats = close_timeline_end(beats, chapter_t1)
    beats = assign_beat_paths(beats, chapter_index=idx, slug=slug)

    expected = sum(count_expected_frame_files(b) for b in beats)
    written = extract_beat_frames(
        video_path,
        beats,
        chapter_t0=chapter_t0,
        bundle_dir=bundle_dir,
    )
    if written != expected:
        raise RuntimeError(f"frame extract: {written}/{expected} ok")

    has_motion = any(beat_kind(b) == BEAT_KIND_MOTION for b in beats)
    row = dict(scene)
    row["beats"] = beats
    row["beat_mode"] = "human_curated_motion" if has_motion else beat_mode
    row["beat_source"] = beat_source
    row["frames"] = [{"id": b["id"], "t": b["t0"], "path": b["path"]} for b in beats]
    row["frame"] = beats[0]["path"] if beats else row.get("frame")
    return row
