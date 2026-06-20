#!/usr/bin/env python3
"""Sample times and paths for Lalabook chapter visual burst (watch, not poster)."""

from __future__ import annotations

from typing import Any


def chapter_sample_times(
    t0: float,
    t1: float,
    *,
    interval_sec: float = 12.0,
    min_frames: int = 4,
    max_frames: int = 24,
) -> list[float]:
    """Evenly spaced absolute timestamps inside [t0, t1] (inclusive endpoints)."""
    start = float(t0)
    end = float(t1)
    dur = max(0.1, end - start)
    interval = max(1.0, float(interval_sec))
    lo = max(1, int(min_frames))
    hi = max(lo, int(max_frames))
    n = max(lo, min(hi, int(dur / interval) + 1))
    if n <= 1:
        return [round(start + dur * 0.5, 3)]
    step = dur / (n - 1)
    return [round(start + i * step, 3) for i in range(n)]


def burst_frame_rel_paths(
    *,
    chapter_index: int,
    slug: str,
    times: list[float],
    t0: float,
) -> list[dict[str, Any]]:
    """Manifest ``frames[]`` entries (relative paths under bundle)."""
    idx = int(chapter_index)
    chapter_dir = f"frames/{idx:02d}-{slug}"
    out: list[dict[str, Any]] = []
    for i, t_abs in enumerate(times):
        name = f"f{i:04d}.jpg"
        out.append(
            {
                "id": f"v{i:03d}",
                "t": round(float(t_abs) - float(t0), 3),
                "path": f"{chapter_dir}/{name}",
            }
        )
    return out
