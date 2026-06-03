#!/usr/bin/env python3
"""Teacher lesson plan: manifest frame → math episodic (lab authoring, not runtime oracle)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Per-frame teacher events (cue, correct, concept_id)
_FRAME_MATH: dict[str, tuple[str, str, str] | None] = {
    "count-1-dot": ("1", "1", "math.num.one"),
    "count-2-dots": ("2", "2", "math.num.two"),
    "count-3-dots": ("3", "3", "math.num.three"),
    "count-2-grains": ("2", "2", "math.num.two"),
    "count-2-cows": ("2", "2", "math.num.two"),
    "count-2-shapes": ("2", "2", "math.num.two"),
    "count-3-shapes": ("3", "3", "math.num.three"),
    "count-4-shapes": ("4", "4", "math.num.four"),
    "count-5-shapes": ("5", "5", "math.num.five"),
    "count-mixed-3c-2s-2r": ("3", "3", "math.num.three"),
    "count-mixed-3c-2s-2r-labeled": ("3+2+2", "7", "math.op.add"),
    "numberline-0-3": ("3", "3", "math.num.three"),
    "grid-square-2x2": ("4", "4", "math.num.four"),
    "grid-square-3x3": ("9", "9", "math.num.nine"),
    "grid-rect-4x2": ("8", "8", "math.num.eight"),
    "grid-rect-3x2": ("6", "6", "math.num.six"),
    "numberline-mark-1": ("1", "1", "math.num.one"),
    "numberline-mark-2": ("2", "2", "math.num.two"),
    "numberline-mark-3": ("3", "3", "math.num.three"),
    "numberline-compare-3gt2": ("3>2", "3>2", "math.compare.gt"),
    "numberline-compare-2lt3": ("2<3", "2<3", "math.compare.lt"),
    "numberline-lengths-2-and-3": ("2+3", "5", "math.op.add"),
    "numberline-add-2plus3": ("2+3", "5", "math.op.add"),
    "numberline-lengths-5-and-2": ("5-2", "3", "math.op.sub"),
    "numberline-sub-5minus2": ("5-2", "3", "math.op.sub"),
    "numberline-add-3plus2": ("3+2", "5", "math.op.add"),
    "numberline-add-2plus3-comm": ("2+3", "5", "math.op.add"),
    "grid-6x3": ("6", "6", "math.num.six"),
    "grid-multiply-6x3": ("6*3", "18", "math.op.mul"),
    "grid-multiply-3x2": ("3*2", "6", "math.op.mul"),
    "grid-divide-6by3": ("6/3", "2", "math.op.div"),
    "grid-divide-6by2": ("6/2", "3", "math.op.div"),
    "grid-divide-8by4": ("8/4", "2", "math.op.div"),
    "fraction-half": ("1/2", "1/2", "math.num.fraction"),
    "fraction-third": ("1/3", "1/3", "math.num.fraction"),
    "fraction-two-thirds": ("2/3", "2/3", "math.num.fraction"),
    "fraction-three-quarters": ("3/4", "3/4", "math.num.fraction"),
    "fraction-third-6strip": ("6/3", "2", "math.op.div"),
    # Euler–Venn sets (lab teacher cues; runtime без oracle)
    "venn-two-empty": None,
    "venn-region-disjoint": ("∅", "∅", "math.set.disjoint"),
    "venn-region-intersect": ("∩", "∩", "math.set.intersect"),
    "venn-region-union": ("∪", "∪", "math.set.union"),
    "venn-region-subset": ("⊂", "⊂", "math.set.subset"),
    "venn-region-a-only": ("A\\B", "A\\B", "math.set.difference"),
    "nline-set-intersect": ("∩", "∩", "math.set.intersect"),
    "nline-set-union": ("∪", "∪", "math.set.union"),
    "nline-set-subset": ("⊂", "⊂", "math.set.subset"),
    "nline-set-disjoint": ("∅", "∅", "math.set.disjoint"),
    "nline-set-a-only": ("A\\B", "A\\B", "math.set.difference"),
    # geometry lexicon (lesson-15): Russian word ↔ figure
    "geom-circle": ("круг", "круг", "math.geom.circle"),
    "geom-square": ("квадрат", "квадрат", "math.geom.square"),
    "geom-rectangle": ("прямоугольник", "прямоугольник", "math.geom.rectangle"),
    "geom-stroke": ("линия", "линия", "math.geom.stroke"),
    "geom-segment": ("отрезок", "отрезок", "math.geom.segment"),
    "geom-line": ("прямая", "прямая", "math.geom.line"),
    # pure shape cards — visual only
    "shape-circle": None,
    "shape-square": None,
    "shape-rectangle": None,
}

_CONCEPT_DEFAULTS: dict[str, tuple[str, str]] = {
    "math.num.one": ("1", "1"),
    "math.num.two": ("2", "2"),
    "math.num.three": ("3", "3"),
    "math.num.four": ("4", "4"),
    "math.num.five": ("5", "5"),
    "math.op.add": ("2+3", "5"),
    "math.op.sub": ("5-2", "3"),
    "math.op.mul": ("2*3", "6"),
    "math.op.div": ("6/3", "2"),
    "math.compare.gt": ("3>2", "3>2"),
    "math.compare.lt": ("2<3", "2<3"),
    "math.numberline.point": ("2", "2"),
    "math.numberline.length": ("3", "3"),
    "math.numberline.segment": ("0", "3"),
    "math.num.fraction": ("1/2", "1/2"),
    "math.set.intersect": ("∩", "∩"),
    "math.set.union": ("∪", "∪"),
    "math.set.subset": ("⊂", "⊂"),
    "math.set.disjoint": ("∅", "∅"),
    "math.set.difference": ("A\\B", "A\\B"),
    "math.geom.circle": ("круг", "круг"),
    "math.geom.square": ("квадрат", "квадрат"),
    "math.geom.rectangle": ("прямоугольник", "прямоугольник"),
    "math.geom.stroke": ("линия", "линия"),
    "math.geom.segment": ("отрезок", "отрезок"),
    "math.geom.line": ("прямая", "прямая"),
}


def _math_from_tags(frame: dict[str, Any]) -> dict[str, str] | None:
    for tag in frame.get("curriculum_tags") or []:
        tid = str(tag)
        if not tid.startswith("math."):
            continue
        cue, correct = _CONCEPT_DEFAULTS.get(tid, (tid.rsplit(".", 1)[-1], tid.rsplit(".", 1)[-1]))
        fid = str(frame.get("id") or "")
        m = re.search(r"(\d+)x(\d+)", fid)
        if m and tid == "math.op.mul":
            a, b = m.group(1), m.group(2)
            cue = f"{a}*{b}"
            correct = str(int(a) * int(b))
        m = re.search(r"(\d+)by(\d+)", fid)
        if m and tid == "math.op.div":
            a, b = m.group(1), m.group(2)
            cue = f"{a}/{b}"
            correct = str(int(a) // int(b))
        return {"cue": cue, "correct": correct, "concept_id": tid}
    return None


def math_spec_for_frame(frame: dict[str, Any]) -> dict[str, str] | None:
    fid = str(frame.get("id") or "")
    row = _FRAME_MATH.get(fid)
    if row is None and fid not in _FRAME_MATH:
        cid = str(frame.get("concept_id") or "")
        if cid.startswith("math."):
            cue, correct = _CONCEPT_DEFAULTS.get(cid, (cid, cid))
            return {"cue": cue, "correct": correct, "concept_id": cid}
        return _math_from_tags(frame)
    if row is None:
        return None
    cue, correct, cid = row
    return {"cue": cue, "correct": correct, "concept_id": cid}


def build_moment_steps(manifest: dict[str, Any], stage_id: str) -> list[dict[str, Any]]:
    stages = {str(s.get("id") or ""): s for s in manifest.get("stages") or []}
    stage = stages.get(stage_id)
    if not stage:
        raise ValueError(f"unknown stage: {stage_id}")

    lesson_ids = {str(x) for x in stage.get("lesson_ids") or []}
    frames = [
        f
        for f in manifest.get("frames") or []
        if str(f.get("lesson_id") or "") in lesson_ids
    ]
    order = {str(s.get("id") or ""): int(s.get("order") or 0) for s in manifest.get("stages") or []}
    frames.sort(key=lambda f: (order.get(stage_id, 0), str(f.get("id") or "")))

    steps: list[dict[str, Any]] = []
    for frame in frames:
        fid = str(frame.get("id") or "")
        steps.append({"visual_frame": fid})
        spec = math_spec_for_frame(frame)
        if spec:
            steps.append({"math": {**spec, "scene": f"moment:{stage_id}:{fid}"}})
    return steps


def load_manifest(class_dir: Path, manifest_name: str = "class.manifest.json") -> dict[str, Any]:
    return json.loads((class_dir / manifest_name).read_text(encoding="utf-8"))


def stage_ids_in_order(manifest: dict[str, Any]) -> list[str]:
    stages = sorted(manifest.get("stages") or [], key=lambda s: int(s.get("order") or 0))
    return [str(s.get("id") or "") for s in stages]
