"""Hippo batch hooks (Kolb sessions) + ADR-0088 quad-mode index."""

from casa.prisms.hippo.mode import (
    HIPPO_MODE_CONSOLIDATE,
    HIPPO_MODE_IDLE_MICRO,
    HIPPO_MODE_INTEGRATE,
    HIPPO_MODE_WAKE,
    get_hippo_mode,
    set_hippo_mode,
)
from casa.prisms.hippo.wake_index import (
    close_episode_boundary,
    close_moment_boundary,
    ensure_hippo_index,
    hippo_wake_index_tick,
)

__all__ = [
    "HIPPO_MODE_WAKE",
    "HIPPO_MODE_CONSOLIDATE",
    "HIPPO_MODE_INTEGRATE",
    "HIPPO_MODE_IDLE_MICRO",
    "get_hippo_mode",
    "set_hippo_mode",
    "ensure_hippo_index",
    "hippo_wake_index_tick",
    "close_episode_boundary",
    "close_moment_boundary",
]
