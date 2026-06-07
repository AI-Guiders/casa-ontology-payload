"""Working Memory Prism — constants and shared helpers."""

from __future__ import annotations

import re
from typing import Any

DEFAULT_SCRATCH_LATTICE = "agent-wm-scratch"
WM_CONCEPT_PREFIX = "agent.wm."
WM_SCENE_TAG = "H3_scene"
DEFAULT_SCRATCH_TTL = 32

DEFAULT_WM_POLICY: dict[str, Any] = {
    "theta_decay": 0.20,
    "theta_hold": 0.45,
    "theta_promote": 0.65,
    "prune_every_ticks": 8,
    "max_scratch_lattices": 3,
    "scratch_ttl_ticks": DEFAULT_SCRATCH_TTL,
    "score_weights": {
        "reuse": 0.25,
        "surprise_drop": 0.20,
        "cross_cue": 0.20,
        "partner_callback": 0.15,
        "anti_paste": 0.10,
        "one_shot": -0.30,
        "high_paste": -0.25,
    },
}

PARTNER_CALLBACK_CUES = (
    "как мы говорили",
    "мы говорили",
    "напомни",
    "продолж",
    "контекст",
    "связь между",
    "про это",
)

MODALITY_ORDER = ("dialogue", "text", "vis", "math")


def slug(text: str, *, max_len: int = 28) -> str:
    slug_text = re.sub(r"[^a-z0-9_-]+", "-", str(text or "").lower()).strip("-")
    return slug_text[:max_len] or "node"


def tokenize(text: str) -> set[str]:
    return {
        t.lower()
        for t in re.findall(r"[\w\u0400-\u04FF]+", text, flags=re.UNICODE)
        if len(t) > 2
    }
