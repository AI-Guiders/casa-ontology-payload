#!/usr/bin/env python3
"""Deliberate practice — weakest_link focus after Check fail (4C/ID JIT)."""

from __future__ import annotations

from typing import Any

from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.tick import ControlExtensions


def _segment_weakness(segment: dict[str, Any]) -> tuple[int, dict[str, Any]] | None:
    verdict = str(segment.get("verdict") or "")
    if verdict not in ("ambiguous", "wrong", "empty", "unknown"):
        return None
    score = int(segment.get("top_score") or 0)
    leaders = segment.get("leaders") or []
    ambiguity = max(0, len(leaders) - 1)
    priority = ambiguity * 10 + (4 - min(score, 4))
    return priority, segment


def weakest_link_from_probe_report(report: dict[str, Any]) -> dict[str, Any] | None:
    """Pick one weak segment from phrase/analytic probe reports."""
    best: tuple[int, dict[str, Any], dict[str, Any]] | None = None

    for word in report.get("word_reads") or []:
        if not isinstance(word, dict):
            continue
        chain = word.get("chain") if isinstance(word.get("chain"), dict) else {}
        for seg in chain.get("segments") or []:
            if not isinstance(seg, dict):
                continue
            hit = _segment_weakness(seg)
            if hit is None:
                continue
            pri, segment = hit
            if best is None or pri > best[0]:
                best = (pri, segment, word)

    if best is None:
        for item in report.get("items") or []:
            if not isinstance(item, dict):
                continue
            v = str(item.get("verdict") or "")
            if v in ("know", "analytic_know"):
                continue
            pri = 5 if v == "ambiguous" else 8
            if best is None or pri > best[0]:
                best = (
                    pri,
                    {
                        "frame_id": item.get("frame_id"),
                        "teacher_hint": item.get("teacher_hint"),
                        "verdict": v,
                    },
                    item,
                )

    if best is None:
        return None

    _, segment, parent = best
    frame_id = str(segment.get("frame_id") or parent.get("probe_frame_id") or parent.get("frame_id") or "")
    concept_id = str(
        segment.get("teacher_hint")
        or segment.get("concept_id")
        or parent.get("word_concept_id")
        or ""
    )
    return {
        "kind": "weakest_link",
        "frame_id": frame_id,
        "concept_id": concept_id,
        "verdict": segment.get("verdict"),
        "surface": parent.get("surface"),
        "parent_slug": parent.get("slug"),
    }


def weakest_link_from_surprise(
    control: ControlExtensions,
    *,
    hippo_ep: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    candidates = [str(c) for c in control.surprise if str(c).strip()]
    if hippo_ep:
        correct = str(hippo_ep.get("correct") or "")
        for token in correct.replace(",", " ").split():
            t = token.strip()
            if t and t not in candidates:
                candidates.append(t)

    for cid in candidates:
        if cid.startswith("syllable."):
            syllable = cid.split(".", 1)[-1]
            return {
                "kind": "weakest_link",
                "concept_id": cid,
                "frame_id": f"syllable-{syllable}-sans",
                "verdict": "surprise",
            }
        if cid.startswith("lang.word."):
            slug = cid.split(".", 2)[-1]
            return {
                "kind": "weakest_link",
                "concept_id": cid,
                "frame_id": f"word-{slug}-sans",
                "verdict": "surprise",
            }
    if candidates:
        return {"kind": "weakest_link", "concept_id": candidates[0], "verdict": "surprise"}
    return None


def apply_deliberate_practice(
    wm: WorkingMemory,
    link: dict[str, Any] | None,
    *,
    goal_prefix: str = "goal.practice",
) -> dict[str, Any] | None:
    if not link:
        return None
    cid = str(link.get("concept_id") or "").strip()
    frame_id = str(link.get("frame_id") or "").strip()
    if frame_id:
        wm.step_focus = frame_id
    if cid:
        tail = cid.split(".")[-1][:24]
        wm.goal_id = f"{goal_prefix}.{tail}"
        wm.goal = f"practice:{cid}"
        wm.subgoal = "deliberate_practice"
    if not wm.step_capability:
        wm.step_capability = "skill.read.analytic"
    return {**link, "applied": True, "goal_id": wm.goal_id, "step_focus": wm.step_focus}
