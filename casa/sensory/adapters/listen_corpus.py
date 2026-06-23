#!/usr/bin/env python3
"""Listen corpus adapter — manifest scenes → resolved media paths (ADR-0027 file_replay)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from casa.domain.listen_beat_model import resolve_scene_beat_timeline
from casa.sensory.adapters.media_path import resolve_media_path
from casa.sensory.contracts import (
    BACKEND_FILE_REPLAY,
    BACKEND_FILE_REPLAY_STREAM,
    ListenCorpusCapture,
    ListenStreamCapture,
)


def resolve_scene_frames(
    store_dir: Path | None,
    scene: dict[str, Any],
    *,
    manifest_dir: Path | None = None,
) -> list[tuple[Path, str, float | None]]:
    """Return (path, frame_id_suffix, t_rel_sec) — legacy frames[] or single frame."""
    bases = (manifest_dir, store_dir)
    beat_plans = resolve_scene_beat_timeline(scene, bases)
    if beat_plans:
        out: list[tuple[Path, str, float | None]] = []
        for plan in beat_plans:
            for path, suffix in plan["visuals"]:
                out.append((path, suffix, plan["t0"]))
        return out

    raw: list[tuple[str, str, float | None]] = []
    frames = scene.get("frames")
    if isinstance(frames, list) and frames:
        for i, item in enumerate(frames):
            if isinstance(item, dict):
                ref = str(item.get("path") or item.get("file") or "").strip()
                fid = str(item.get("id") or f"v{i:03d}").strip() or f"v{i:03d}"
                t_raw = item.get("t")
                t_val = float(t_raw) if t_raw is not None else None
            elif isinstance(item, str):
                ref = item.strip()
                fid = f"v{i:03d}"
                t_val = None
            else:
                continue
            if ref:
                raw.append((ref, fid, t_val))

    if not raw:
        single = str(scene.get("frame") or scene.get("frame_path") or "").strip()
        if single:
            raw.append((single, "v000", None))

    out = []
    for ref, fid, t_val in raw:
        path = resolve_media_path(ref, bases)
        if path is not None:
            out.append((path, fid, t_val))
    return out


def resolve_scene_frame(store_dir: Path | None, scene: dict[str, Any]) -> Path | None:
    entries = resolve_scene_frames(store_dir, scene)
    return entries[0][0] if entries else None


def resolve_scene_beats(
    store_dir: Path | None,
    scene: dict[str, Any],
    *,
    manifest_dir: Path | None = None,
) -> list[tuple[Path, str, float, float]]:
    """Legacy: first visual per beat — (path, beat_id, t0_rel, t1_rel)."""
    bases = (manifest_dir, store_dir)
    out: list[tuple[Path, str, float, float]] = []
    for plan in resolve_scene_beat_timeline(scene, bases):
        if not plan["visuals"]:
            continue
        path, _suffix = plan["visuals"][0]
        out.append((path, plan["beat_id"], plan["t0"], plan["t1"]))
    return out


def resolve_scene_wav(
    store_dir: Path | None,
    scene: dict[str, Any],
    *,
    manifest_dir: Path | None = None,
) -> Path | None:
    wav = str(scene.get("wav") or "").strip()
    if not wav:
        return None
    return resolve_media_path(wav, (manifest_dir, store_dir))


def find_bundle_video(bundle_dir: Path) -> Path:
    for ext in ("mp4", "webm", "mkv"):
        candidate = bundle_dir / f"video.{ext}"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"no video.* in {bundle_dir}")


def load_chapter_scene(manifest: Path, chapter: int) -> dict[str, Any]:
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        scene = json.loads(line)
        if int(scene.get("chapter_index", -1)) == chapter:
            return scene
    raise ValueError(f"chapter {chapter} not found in {manifest}")


def capture_listen_scene(
    scene: dict[str, Any],
    *,
    store_dir: Path | None = None,
    manifest_dir: Path | None = None,
    wav_path: Path | str | None = None,
    frame_path: Path | str | None = None,
) -> ListenCorpusCapture:
    """Adapter: manifest scene dict → resolved corpus capture (no imprint)."""
    sid = str(scene.get("id") or "")
    bases = (manifest_dir, store_dir)
    beat_plans = resolve_scene_beat_timeline(scene, bases)

    resolved_wav: Path | None = None
    if wav_path is not None:
        wp = Path(wav_path)
        resolved_wav = wp if wp.is_file() else None
    else:
        resolved_wav = resolve_scene_wav(store_dir, scene, manifest_dir=manifest_dir)

    if frame_path is not None:
        fp = Path(frame_path)
        frame_entries = [(fp, "v000", None)] if fp.is_file() else []
        beat_plans = []
    elif beat_plans:
        frame_entries: list[tuple[Path, str, float | None]] = []
    else:
        frame_entries = resolve_scene_frames(store_dir, scene, manifest_dir=manifest_dir)

    return ListenCorpusCapture(
        backend_id=BACKEND_FILE_REPLAY,
        scene_id=sid,
        scene=dict(scene),
        wav_path=resolved_wav,
        frame_entries=frame_entries,
        beat_plans=beat_plans,
        store_dir=store_dir,
        manifest_dir=manifest_dir,
    )


def capture_listen_stream(
    scene: dict[str, Any],
    *,
    bundle_dir: Path,
    store_dir: Path | None = None,
    video_path: Path | None = None,
    wav_path: Path | None = None,
) -> ListenStreamCapture:
    """Adapter: chapter scene + bundle → stream capture (video file + optional wav)."""
    manifest_dir = bundle_dir.resolve()
    sid = str(scene.get("id") or "scene")
    stream_id = str(scene.get("stream_id") or sid)
    video = video_path.resolve() if video_path is not None else find_bundle_video(manifest_dir)
    wav = wav_path
    if wav is None:
        wav = resolve_scene_wav(store_dir, scene, manifest_dir=manifest_dir)
    chapter_t0 = float(scene.get("t0") or 0.0)
    chapter_t1 = float(scene.get("t1") or chapter_t0)
    return ListenStreamCapture(
        backend_id=BACKEND_FILE_REPLAY_STREAM,
        scene_id=sid,
        stream_id=stream_id,
        scene=dict(scene),
        video_path=video,
        wav_path=wav,
        chapter_t0=chapter_t0,
        chapter_t1=chapter_t1,
        store_dir=store_dir,
        manifest_dir=manifest_dir,
    )
