#!/usr/bin/env python3
"""Teacher plan: visual ABC card → lexical episodic (lab authoring)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_manifest(class_dir: Path) -> dict[str, Any]:
    return json.loads((class_dir / "class.manifest.json").read_text(encoding="utf-8"))


def stage_ids_in_order(manifest: dict[str, Any]) -> list[str]:
    stages = sorted(manifest.get("stages") or [], key=lambda s: int(s.get("order") or 0))
    return [str(s.get("id") or "") for s in stages if s.get("id")]


def lexical_spec_for_frame(frame: dict[str, Any]) -> dict[str, str] | None:
    letter = str(frame.get("letter") or "").strip()
    word = str(frame.get("word") or "").strip()
    gr = str(frame.get("grapheme") or letter.lower()).strip()
    cid = str(frame.get("concept_id") or f"grapheme.cyrl.{gr}")
    if not letter and not gr:
        return None
    cue = letter or gr.upper()
    surface = word or cue
    return {"cue": cue, "word": surface, "correct": surface, "concept_id": cid}


def build_lexical_moment_steps(manifest: dict[str, Any], stage_id: str) -> list[dict[str, Any]]:
    stages = {str(s.get("id") or ""): s for s in manifest.get("stages") or []}
    stage = stages.get(stage_id)
    if not stage:
        raise ValueError(f"unknown stage: {stage_id}")

    lesson_ids = {str(x) for x in stage.get("lesson_ids") or []}
    frames = [
        f for f in manifest.get("frames") or [] if str(f.get("lesson_id") or "") in lesson_ids
    ]
    frames.sort(key=lambda f: str(f.get("grapheme") or f.get("letter") or f.get("id") or ""))

    steps: list[dict[str, Any]] = []
    for frame in frames:
        fid = str(frame.get("id") or "")
        steps.append({"visual_frame": fid})
        spec = lexical_spec_for_frame(frame)
        if spec:
            steps.append({"lexical": {**spec, "scene": f"moment:{stage_id}:{fid}"}})
    return steps
