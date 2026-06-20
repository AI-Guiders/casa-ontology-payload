#!/usr/bin/env python3
"""Scene-cut beats inside a chapter window — paired A/V boundaries for Lalabook."""

from __future__ import annotations

import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from casa.sensory.load_rgb_frame import load_rgb_frame
from casa.sensory.rgb_frame import RgbFrame

_PTS_RE = re.compile(r"pts_time:(?P<t>[0-9.]+)")


def _ffmpeg_cmd() -> list[str]:
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError("ffmpeg not found on PATH")
    return [path]


def _rgb_pixels_diff(a: RgbFrame, b: RgbFrame, *, y_min: int = 0) -> float:
    if a.width != b.width or a.height != b.height or len(a.rgb) != len(b.rgb):
        return 1.0
    w, h = a.width, a.height
    y_min = max(0, min(h - 1, int(y_min)))
    total = 0
    count = 0
    for y in range(y_min, h):
        for x in range(w):
            i = (y * w + x) * 3
            total += abs(a.rgb[i] - b.rgb[i]) + abs(a.rgb[i + 1] - b.rgb[i + 1]) + abs(a.rgb[i + 2] - b.rgb[i + 2])
            count += 3
    if count <= 0:
        return 0.0
    return total / (count * 255.0)


def _rgb_mean_diff(a: RgbFrame, b: RgbFrame) -> float:
    return _rgb_pixels_diff(a, b, y_min=0)


def _text_band_diff(a: RgbFrame, b: RgbFrame, *, band_fraction: float = 0.5) -> float:
    """Lalabook burns dialogue into lower/mid field — text appears without full-scene swap."""
    band = max(0.2, min(0.85, float(band_fraction)))
    y_min = int(a.height * (1.0 - band))
    return _rgb_pixels_diff(a, b, y_min=y_min)


def _visual_change_score(prev: RgbFrame, frame: RgbFrame) -> float:
    full = _rgb_mean_diff(prev, frame)
    text = _text_band_diff(prev, frame)
    return max(full, text * 1.15)


def _extract_thumb_jpg(video_path: Path, *, t_abs: float, out_jpg: Path) -> bool:
    out_jpg.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        *_ffmpeg_cmd(),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{float(t_abs):.3f}",
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        "-vf",
        "scale=128:-1",
        "-q:v",
        "8",
        str(out_jpg),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode == 0 and out_jpg.is_file()


def _load_thumb(video_path: Path, tmp: Path, tag: str, t_abs: float) -> RgbFrame | None:
    thumb = tmp / f"{tag}.jpg"
    if not _extract_thumb_jpg(video_path, t_abs=t_abs, out_jpg=thumb):
        return None
    return load_rgb_frame(thumb)


def detect_illustration_cut_times(
    video_path: Path,
    *,
    t0: float,
    t1: float,
    sample_interval_sec: float = 0.5,
    diff_threshold: float = 0.028,
    text_diff_threshold: float = 0.018,
    min_gap_sec: float = 1.2,
) -> list[float]:
    """Detect illustration swaps and burned-in text appearances."""
    video_path = Path(video_path)
    start = float(t0)
    end = float(t1)
    step = max(0.25, float(sample_interval_sec))
    full_thr = max(0.008, min(0.5, float(diff_threshold)))
    text_thr = max(0.005, min(0.5, float(text_diff_threshold)))
    gap = max(0.4, float(min_gap_sec))
    times = [round(start + i * step, 3) for i in range(int((end - start) / step) + 1)]
    times = [t for t in times if start <= t < end]
    if not times:
        return [start]

    cuts: list[float] = [start]
    with tempfile.TemporaryDirectory(prefix="casa-illus-cuts-") as tmp:
        tmp_path = Path(tmp)
        prev = _load_thumb(video_path, tmp_path, "t00000", times[0])
        for i, t in enumerate(times[1:], start=1):
            frame = _load_thumb(video_path, tmp_path, f"t{i:05d}", t)
            if prev is None or frame is None:
                if frame is not None:
                    prev = frame
                continue
            full = _rgb_mean_diff(prev, frame)
            text = _text_band_diff(prev, frame)
            if (full >= full_thr or text >= text_thr) and t - cuts[-1] >= gap:
                cuts.append(t)
            prev = frame
    return cuts


def representative_frame_time(
    video_path: Path,
    *,
    beat_t0_abs: float,
    beat_t1_abs: float,
    sample_step_sec: float = 0.35,
) -> float:
    """Pick moment in beat when visuals changed most (text on field), not blank beat start."""
    start = float(beat_t0_abs)
    end = float(beat_t1_abs)
    if end - start <= 0.35:
        return start + 0.1 * (end - start)
    step = max(0.2, float(sample_step_sec))
    times = []
    t = start
    while t < end - 0.05:
        times.append(t)
        t += step
    times.append(max(start, end - 0.12))

    with tempfile.TemporaryDirectory(prefix="casa-beat-pick-") as tmp:
        tmp_path = Path(tmp)
        base = _load_thumb(video_path, tmp_path, "base", times[0])
        if base is None:
            return start + 0.15
        best_t = times[0]
        best_score = 0.0
        for i, sample_t in enumerate(times[1:], start=1):
            frame = _load_thumb(video_path, tmp_path, f"s{i:03d}", sample_t)
            if frame is None:
                continue
            score = _visual_change_score(base, frame)
            if score > best_score:
                best_score = score
                best_t = sample_t
        if best_score < 0.008:
            return start + 0.45 * (end - start)
        return best_t


def detect_scene_cut_times(
    video_path: Path,
    *,
    t0: float,
    t1: float,
    threshold: float = 0.35,
) -> list[float]:
    """Absolute timestamps of scene changes in (t0, t1) via ffmpeg select=gt(scene)."""
    video_path = Path(video_path)
    if not video_path.is_file():
        raise FileNotFoundError(video_path)
    thr = max(0.05, min(0.95, float(threshold)))
    cmd = [
        *_ffmpeg_cmd(),
        "-hide_banner",
        "-loglevel",
        "info",
        "-ss",
        f"{float(t0):.3f}",
        "-to",
        f"{float(t1):.3f}",
        "-i",
        str(video_path),
        "-an",
        "-vf",
        f"select='gt(scene,{thr})',showinfo",
        "-f",
        "null",
        "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "ffmpeg scene detect failed").strip()[:500])
    times: list[float] = []
    for line in (proc.stderr or "").splitlines():
        m = _PTS_RE.search(line)
        if not m:
            continue
        t_abs = float(t0) + float(m.group("t"))
        if float(t0) <= t_abs < float(t1):
            times.append(round(t_abs, 3))
    return sorted(set(times))


def merge_close_cuts(times: list[float], *, min_gap_sec: float = 2.0) -> list[float]:
    if not times:
        return []
    gap = max(0.4, float(min_gap_sec))
    out = [times[0]]
    for t in times[1:]:
        if t - out[-1] >= gap:
            out.append(t)
    return out


def split_long_beat_windows(
    windows: list[tuple[float, float]],
    *,
    max_beat_sec: float = 6.0,
) -> list[tuple[float, float]]:
    """Safety: Lalabook line + text rarely holds >6s on one still."""
    cap = max(2.0, float(max_beat_sec))
    out: list[tuple[float, float]] = []
    for bt0, bt1 in windows:
        dur = bt1 - bt0
        if dur <= cap:
            out.append((bt0, bt1))
            continue
        n = max(2, int(math.ceil(dur / cap)))
        step = dur / n
        for i in range(n):
            out.append((round(bt0 + i * step, 3), round(bt0 + (i + 1) * step, 3)))
    return out


def cuts_to_beat_windows(
    cut_times: list[float],
    *,
    t0: float,
    t1: float,
    min_beats: int = 3,
    max_beats: int = 80,
    min_beat_sec: float = 0.8,
    max_beat_sec: float = 6.0,
) -> list[tuple[float, float]]:
    start = float(t0)
    end = float(t1)
    dur = max(0.1, end - start)
    rel_cuts = [0.0]
    for t in cut_times:
        rel = round(t - start, 3)
        if 0.0 < rel < dur:
            rel_cuts.append(rel)
    rel_cuts = sorted(set(rel_cuts))
    rel_cuts = merge_close_cuts(rel_cuts, min_gap_sec=min_beat_sec)
    if rel_cuts[0] != 0.0:
        rel_cuts.insert(0, 0.0)

    beats: list[tuple[float, float]] = []
    for i, bt0 in enumerate(rel_cuts):
        bt1 = rel_cuts[i + 1] if i + 1 < len(rel_cuts) else dur
        seg = (round(bt0, 3), round(bt1, 3))
        if seg[1] <= seg[0]:
            continue
        if beats and (seg[1] - seg[0]) < min_beat_sec:
            beats[-1] = (beats[-1][0], seg[1])
        else:
            beats.append(seg)

    if not beats:
        beats = [(0.0, round(dur, 3))]
    elif beats[0][0] > 0:
        beats[0] = (0.0, beats[0][1])
    if beats[-1][1] < dur - 0.05:
        beats[-1] = (beats[-1][0], round(dur, 3))

    beats = split_long_beat_windows(beats, max_beat_sec=max_beat_sec)

    if len(beats) < min_beats and dur >= min_beats * min_beat_sec:
        n = min(max_beats, max(min_beats, int(dur / max_beat_sec) + 1))
        step = dur / n
        beats = [(round(i * step, 3), round((i + 1) * step, 3)) for i in range(n)]
        beats[-1] = (beats[-1][0], round(dur, 3))

    if len(beats) > max_beats:
        merged = list(beats)
        while len(merged) > max_beats and len(merged) > 1:
            best = min(
                range(len(merged) - 1),
                key=lambda i: merged[i + 1][1] - merged[i][0],
            )
            merged[best : best + 2] = [(merged[best][0], merged[best + 1][1])]
        beats = merged

    return beats


def beat_manifest_rows(
    *,
    chapter_index: int,
    slug: str,
    windows: list[tuple[float, float]],
    frame_times: list[float] | None = None,
) -> list[dict[str, Any]]:
    chapter_dir = f"frames/{int(chapter_index):02d}-{slug}"
    rows: list[dict[str, Any]] = []
    for i, (bt0, bt1) in enumerate(windows):
        bid = f"b{i:03d}"
        row: dict[str, Any] = {
            "id": bid,
            "t0": bt0,
            "t1": bt1,
            "path": f"{chapter_dir}/{bid}.jpg",
        }
        if frame_times is not None and i < len(frame_times):
            row["frame_t"] = round(float(frame_times[i]), 3)
        rows.append(row)
    return rows


def extract_beat_frame(
    video_path: Path,
    *,
    t_abs: float,
    out_jpg: Path,
) -> bool:
    video_path = Path(video_path)
    out_jpg = Path(out_jpg)
    out_jpg.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        *_ffmpeg_cmd(),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{max(0.0, float(t_abs)):.3f}",
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(out_jpg),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode == 0 and out_jpg.is_file()


def extract_chapter_beats(
    video_path: Path,
    *,
    t0: float,
    t1: float,
    out_dir: Path,
    chapter_index: int,
    slug: str,
    scene_threshold: float = 0.35,
    min_beats: int = 3,
    max_beats: int = 80,
    illustration_diff_threshold: float = 0.028,
    text_diff_threshold: float = 0.018,
    sample_interval_sec: float = 0.5,
    max_beat_sec: float = 6.0,
) -> list[dict[str, Any]]:
    illus_cuts = detect_illustration_cut_times(
        video_path,
        t0=t0,
        t1=t1,
        sample_interval_sec=sample_interval_sec,
        diff_threshold=illustration_diff_threshold,
        text_diff_threshold=text_diff_threshold,
    )
    ffmpeg_cuts = detect_scene_cut_times(video_path, t0=t0, t1=t1, threshold=scene_threshold)
    merged = sorted(set(illus_cuts) | set(ffmpeg_cuts))
    windows = cuts_to_beat_windows(
        merged,
        t0=t0,
        t1=t1,
        min_beats=min_beats,
        max_beats=max_beats,
        max_beat_sec=max_beat_sec,
    )
    start = float(t0)
    frame_times: list[float] = []
    for bt0, bt1 in windows:
        frame_times.append(
            representative_frame_time(
                video_path,
                beat_t0_abs=start + bt0,
                beat_t1_abs=start + bt1,
            )
        )
    frame_times_rel = [round(ft - start, 3) for ft in frame_times]
    rows = beat_manifest_rows(
        chapter_index=chapter_index,
        slug=slug,
        windows=windows,
        frame_times=frame_times_rel,
    )
    written: list[dict[str, Any]] = []
    for row, frame_t in zip(rows, frame_times, strict=True):
        out_jpg = out_dir / Path(str(row["path"])).name
        if extract_beat_frame(video_path, t_abs=frame_t, out_jpg=out_jpg):
            written.append(row)
    return written
