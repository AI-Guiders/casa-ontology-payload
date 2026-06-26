#!/usr/bin/env python3
"""Listen moment routing from manifest fields — no kind taxonomy."""

from __future__ import annotations

from typing import Any


def scene_words(scene: dict[str, Any]) -> list[str]:
    """Explicit word tokens only (reading lesson / teacher); not inferred from audio."""
    return [str(w).strip().lower() for w in (scene.get("words") or []) if str(w).strip()]


def scene_speakers(scene: dict[str, Any]) -> list[str]:
    out: list[str] = []
    multi = scene.get("speakers")
    if isinstance(multi, list):
        for item in multi:
            slug = str(item or "").strip().lower()
            if slug and slug not in out:
                out.append(slug)
    one = str(scene.get("speaker") or "").strip().lower()
    if one and one not in out:
        out.insert(0, one)
    return out


def wants_lexical_imprint(words: list[str]) -> bool:
    """L2/L3 word tokens only when manifest explicitly supplies words."""
    return bool(words)


def is_multi_speaker(speakers: list[str]) -> bool:
    return len(speakers) >= 2


def moment_has_sensory_input(*, wav: bool, frame: bool) -> bool:
    return wav or frame
