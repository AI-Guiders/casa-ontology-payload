"""Beat id lookup by chapter-relative time — no sensory imports (ADR-0088 slice 1)."""

from __future__ import annotations

from typing import Any


def resolve_beat_id_at_t_rel(scene: dict[str, Any], t_rel: float) -> str | None:
    """Return beat id for chapter-relative ``t_rel`` using half-open ``[t0, t1)`` spans.

    Adjacent beats share boundaries (``beat[i].t1 == beat[i+1].t0``); the later beat wins
    at the shared timestamp. The final beat uses a closed right edge ``[t0, t1]`` so the
    chapter end tick still resolves.
    """
    beats = scene.get("beats")
    if not isinstance(beats, list) or not beats:
        return None
    t = float(t_rel)
    eps = 1e-6
    last_idx = len(beats) - 1
    for i, item in enumerate(beats):
        if not isinstance(item, dict):
            continue
        try:
            t0 = float(item["t0"])
            t1 = float(item["t1"])
        except (KeyError, TypeError, ValueError):
            continue
        if t < t0 - eps:
            continue
        bid = str(item.get("id") or f"b{i:03d}").strip()
        if not bid:
            continue
        if i == last_idx:
            if t <= t1 + eps:
                return bid
        elif t < t1 - eps:
            return bid
    return None
