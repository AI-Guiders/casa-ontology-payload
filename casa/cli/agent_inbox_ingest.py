#!/usr/bin/env python3
"""Route teacher inbox payloads into a living agent store (shared state aware)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa._paths import REPO_ROOT
from casa.cli.feed_arithmetic_stream import feed_arithmetic_stream
from casa.cli.ingest_lesson_moment import ingest_lesson_moment
from casa.cli.ingest_lang_lesson_class import ingest_lang_lesson_class
from casa.cli.ingest_lesson_class import ingest_lesson_class
from casa.cli.ingest_visual_class import ingest_visual_class


def ingest_inbox_payload(
    store_dir: Path,
    payload: dict[str, Any],
    *,
    state: dict | None = None,
    persist: bool | None = None,
) -> dict[str, Any]:
    """Dispatch inbox JSON to the matching ingest entry point."""
    kind = str(payload.get("kind") or payload.get("type") or "").strip().lower()
    write = bool(payload.get("persist", True)) if persist is None else persist

    if kind in ("lesson_class", "math_lesson_class", "math-class"):
        return ingest_lesson_class(
            store_dir,
            (REPO_ROOT / str(payload.get("class_dir") or "")).resolve(),
            lesson_ids=list(payload.get("lesson_ids") or []) or None,
            sleep_after_each_lesson=bool(payload.get("sleep_after_each_lesson", True)),
            persist=write,
            state=state,
        )
    if kind in ("lang_lesson_class", "lang-class"):
        return ingest_lang_lesson_class(
            store_dir,
            (REPO_ROOT / str(payload.get("class_dir") or "")).resolve(),
            lesson_ids=list(payload.get("lesson_ids") or []) or None,
            sleep_after_each_lesson=bool(payload.get("sleep_after_each_lesson", True)),
            persist=write,
            state=state,
        )
    if kind in ("arithmetic_stream", "arith_stream", "arith"):
        return feed_arithmetic_stream(
            store_dir,
            count=int(payload.get("count") or 20),
            max_value=int(payload.get("max_value") or 50),
            seed=(int(payload["seed"]) if "seed" in payload and payload["seed"] is not None else None),
            sleep=bool(payload.get("sleep", True)),
            persist=write,
            state=state,
        )
    if kind in ("visual_lesson_class", "visual-class", "visual_cards"):
        class_dir = (REPO_ROOT / str(payload.get("class_dir") or "lessons/visual-cards")).resolve()
        return ingest_visual_class(
            store_dir,
            class_dir,
            stage_ids=list(payload.get("stage_ids") or payload.get("stage") or []) or None,
            lesson_ids=list(payload.get("lesson_ids") or []) or None,
            frame_ids=list(payload.get("frame_ids") or []) or None,
            sleep_after_stage=bool(
                payload.get("sleep_after_stage", not payload.get("sleep_after_each", False))
            ),
            sleep_after_each=bool(payload.get("sleep_after_each", False)),
            persist=write,
            state=state,
        )
    if kind in ("lesson_moment", "lesson-moment", "moment"):
        class_dir = (REPO_ROOT / str(payload.get("class_dir") or "lessons/visual-cards")).resolve()
        return ingest_lesson_moment(
            store_dir,
            class_dir,
            moment_id=str(payload.get("moment_id") or "") or None,
            steps=list(payload.get("steps") or []) or None,
            stage_ids=list(payload.get("stage_ids") or payload.get("stage") or []) or None,
            frame_ids=list(payload.get("frame_ids") or []) or None,
            math_episodes=list(payload.get("math_episodes") or payload.get("math") or []) or None,
            interleave=str(payload.get("interleave") or "after_each_visual"),  # type: ignore[arg-type]
            sleep=bool(payload.get("sleep", True)),
            persist=write,
            state=state,
        )
    raise ValueError(f"unknown payload kind={kind!r}")
