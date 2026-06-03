#!/usr/bin/env python3
"""Lesson moment — visual + math and/or lexical episodic, one sleep (co-occurrence bridges)."""

from __future__ import annotations

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path
from typing import Any, Literal

from casa.cli.ingest_state import resolve_ingest_state
from casa.cli.moment_plan import build_moment_steps
from casa.cli.ingest_visual_class import (
    _group_frames_by_stage,
    _lesson_ids_for_stages,
    _token_counts,
)
from casa.prisms.memory.lexical_lattice_bootstrap import ensure_lexical_lattices
from casa.prisms.memory.f0_math_ingest import ingest_math_bundle
from casa.prisms.memory.memory_prisms import append_episode, memory_lattices, run_sleep
from casa.prisms.shared.lattice_names_v1 import (
    ALPHABET_EN,
    ALPHABET_RU,
    LEXICON_EN,
    LEXICON_RU,
    SCHEMA_MATH,
    SYLLABLES_EN,
    SYLLABLES_RU,
)
from casa.prisms.shared.store_layout import default_agent_store
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state
from casa.prisms.visual.bootstrap import ensure_prism_visual
from casa.prisms.visual.imprint import imprint_visual_frame
from casa.sensory.load_rgb_frame import load_rgb_frame

Interleave = Literal["after_each_visual", "after_all_visual"]
_EMPTY_BUNDLE: dict[str, Any] = {"claims": [], "graph": {"edges": []}}


def _ensure_schema_math(state: dict) -> None:
    lat = memory_lattices(state).get(SCHEMA_MATH) or {}
    if lat.get("cells") or lat.get("_cells_in_ltm"):
        return
    ingest_math_bundle(state, _EMPTY_BUNDLE, lattice_id=SCHEMA_MATH)


def _emergent_bridge_count(sleep_rep: dict[str, Any]) -> int:
    kinds = ("emergent_crosslink", "emergent_crosslink_lex")
    return sum(1 for item in sleep_rep.get("items") or [] if item.get("kind") in kinds)


def _steps_need_lexical(steps: list[dict[str, Any]] | None) -> bool:
    return bool(steps and any("lexical" in s for s in steps))


def _select_manifest_frames(
    manifest: dict,
    *,
    stage_ids: list[str] | None,
    frame_ids: list[str] | None,
) -> list[dict[str, Any]]:
    filter_lessons = set(_lesson_ids_for_stages(manifest, stage_ids)) if stage_ids else None
    filter_frames = set(frame_ids) if frame_ids else None
    selected: list[dict[str, Any]] = []
    for frame in manifest.get("frames") or []:
        fid = str(frame.get("id") or "")
        lid = str(frame.get("lesson_id") or "")
        if filter_lessons is not None and lid not in filter_lessons:
            continue
        if filter_frames is not None and fid not in filter_frames:
            continue
        selected.append(frame)
    if not selected:
        raise ValueError("no frames matched stage/frame filter")
    return selected


def _imprint_manifest_frame(
    state: dict,
    class_dir: Path,
    frame: dict[str, Any],
    *,
    stage_id: str | None,
) -> dict[str, Any]:
    rel = Path(str(frame.get("path") or ""))
    path = (class_dir / rel).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    fid = str(frame.get("id") or path.stem)
    rgb = load_rgb_frame(path)
    rep = imprint_visual_frame(
        state,
        rgb,
        frame_id=fid,
        scene_label=str(frame.get("scene_label") or "card"),
        record_episode=True,
    )
    return {
        "kind": "visual",
        "id": frame.get("id"),
        "path": str(rel).replace("\\", "/"),
        "scene_label": frame.get("scene_label"),
        "stage_id": stage_id,
        **rep,
    }


def _append_math_moment(
    state: dict,
    spec: dict[str, Any],
    *,
    scene: str,
    bundle: dict[str, Any],
) -> dict[str, Any]:
    cue = str(spec.get("cue") or "").strip()
    if not cue:
        raise ValueError("math step requires cue")
    correct = str(spec.get("correct") if spec.get("correct") is not None else cue)
    concept_id = str(spec.get("concept_id") or "").strip() or None
    ep = append_episode(
        state,
        cue=cue,
        surface_attempt=correct,
        correct=correct,
        lattice_id=SCHEMA_MATH,
        concept_id=concept_id,
        scene=str(spec.get("scene") or scene),
        bundle=bundle,
        episode_source="ingest",
    )
    return {
        "kind": "math",
        "cue": cue,
        "correct": correct,
        "concept_id": concept_id,
        "episode_id": ep.get("id") if ep else None,
    }


def _append_lexical_moment(
    state: dict,
    spec: dict[str, Any],
    *,
    scene: str,
) -> dict[str, Any]:
    cue = str(spec.get("cue") or "").strip()
    if not cue:
        raise ValueError("lexical step requires cue")
    word = str(spec.get("word") or spec.get("surface") or spec.get("correct") or cue)
    correct = str(spec.get("correct") if spec.get("correct") is not None else word)
    concept_id = str(spec.get("concept_id") or "").strip() or None
    lattice_id = str(spec.get("lattice_id") or "").strip()
    if not lattice_id and concept_id:
        if concept_id.startswith("grapheme.latn."):
            lattice_id = ALPHABET_EN
        elif concept_id.startswith("grapheme."):
            lattice_id = ALPHABET_RU
        elif concept_id.startswith("syllable."):
            lattice_id = SYLLABLES_RU
        elif concept_id.startswith("lang.word.") or concept_id.startswith("lang.meta."):
            lattice_id = LEXICON_RU
        if str(spec.get("locale") or "").lower() == "en":
            if concept_id.startswith("lang.word."):
                lattice_id = LEXICON_EN
            elif concept_id.startswith("grapheme."):
                lattice_id = ALPHABET_EN
            elif concept_id.startswith("syllable."):
                lattice_id = SYLLABLES_EN
    if not lattice_id:
        lattice_id = ALPHABET_RU
    ep = append_episode(
        state,
        cue=cue,
        surface_attempt=word,
        correct=correct,
        lattice_id=lattice_id,
        concept_id=concept_id,
        scene=str(spec.get("scene") or scene),
        bundle=_EMPTY_BUNDLE,
        episode_source="ingest",
    )
    return {
        "kind": "lexical",
        "cue": cue,
        "word": word,
        "correct": correct,
        "concept_id": concept_id,
        "episode_id": ep.get("id") if ep else None,
    }


def _run_explicit_steps(
    state: dict,
    class_dir: Path,
    manifest: dict,
    steps: list[dict[str, Any]],
    *,
    bundle: dict[str, Any],
    scene_prefix: str,
) -> list[dict[str, Any]]:
    frame_index = {str(f.get("id") or ""): f for f in manifest.get("frames") or []}
    l2s = {
        str(lid): str(stage.get("id") or "")
        for stage in manifest.get("stages") or []
        for lid in stage.get("lesson_ids") or []
    }
    trace: list[dict[str, Any]] = []
    for step in steps:
        if "visual_frame" in step or "frame_id" in step:
            fid = str(step.get("visual_frame") or step.get("frame_id") or "")
            frame = frame_index.get(fid)
            if frame is None:
                raise ValueError(f"unknown visual_frame: {fid!r}")
            sid = l2s.get(str(frame.get("lesson_id") or ""))
            trace.append(_imprint_manifest_frame(state, class_dir, frame, stage_id=sid))
            continue
        if "math" in step:
            spec = step.get("math") or {}
            if not isinstance(spec, dict):
                raise ValueError("math step must be an object")
            trace.append(
                _append_math_moment(
                    state,
                    spec,
                    scene=f"{scene_prefix}:step",
                    bundle=bundle,
                )
            )
            continue
        if "lexical" in step:
            spec = step.get("lexical") or {}
            if not isinstance(spec, dict):
                raise ValueError("lexical step must be an object")
            trace.append(
                _append_lexical_moment(
                    state,
                    spec,
                    scene=f"{scene_prefix}:step",
                )
            )
            continue
        raise ValueError(f"unknown step: {step!r}")
    return trace


def _run_interleaved_stage(
    state: dict,
    class_dir: Path,
    manifest: dict,
    selected: list[dict[str, Any]],
    math_episodes: list[dict[str, Any]],
    *,
    interleave: Interleave,
    bundle: dict[str, Any],
    scene_prefix: str,
) -> list[dict[str, Any]]:
    trace: list[dict[str, Any]] = []
    stage_groups = _group_frames_by_stage(manifest, selected)
    for stage_id, stage_frames in stage_groups:
        for frame in stage_frames:
            trace.append(_imprint_manifest_frame(state, class_dir, frame, stage_id=stage_id))
            if interleave == "after_each_visual":
                for spec in math_episodes:
                    trace.append(
                        _append_math_moment(
                            state,
                            spec,
                            scene=f"{scene_prefix}:{stage_id}",
                            bundle=bundle,
                        )
                    )
        if interleave == "after_all_visual":
            for spec in math_episodes:
                trace.append(
                    _append_math_moment(
                        state,
                        spec,
                        scene=f"{scene_prefix}:{stage_id}",
                        bundle=bundle,
                    )
                )
    return trace


def ingest_lesson_moment(
    store_dir: Path,
    class_dir: Path,
    *,
    manifest_name: str = "class.manifest.json",
    moment_id: str | None = None,
    steps: list[dict[str, Any]] | None = None,
    stage_ids: list[str] | None = None,
    frame_ids: list[str] | None = None,
    math_episodes: list[dict[str, Any]] | None = None,
    interleave: Interleave = "after_each_visual",
    sleep: bool = True,
    persist: bool = True,
    state: dict | None = None,
    report_path: Path | None = None,
) -> dict[str, Any]:
    """Teacher moment: visual imprint + math episodic in one hippo batch → sleep."""
    store_dir = store_dir.resolve()
    class_dir = class_dir.resolve()
    manifest = json.loads((class_dir / manifest_name).read_text(encoding="utf-8"))
    bundle = _EMPTY_BUNDLE

    if steps is None and stage_ids and not math_episodes:
        steps = []
        for sid in stage_ids:
            steps.extend(build_moment_steps(manifest, str(sid)))

    state = resolve_ingest_state(store_dir, state)
    state.setdefault("store", {})["last_class"] = manifest.get("class_id")
    state["store"]["last_moment"] = moment_id or stage_ids or "custom"

    ensure_prism_visual(state)
    _ensure_schema_math(state)
    if _steps_need_lexical(steps):
        ensure_lexical_lattices(state)

    scene_prefix = f"moment:{moment_id or (stage_ids[0] if stage_ids else 'custom')}"
    if steps:
        step_trace = _run_explicit_steps(
            state, class_dir, manifest, steps, bundle=bundle, scene_prefix=scene_prefix
        )
    else:
        if not stage_ids and not frame_ids:
            raise ValueError("lesson_moment requires steps or stage_ids/frame_ids")
        selected = _select_manifest_frames(
            manifest, stage_ids=stage_ids, frame_ids=frame_ids
        )
        specs = list(math_episodes or [])
        if not specs:
            raise ValueError("lesson_moment requires math_episodes or explicit steps with math")
        step_trace = _run_interleaved_stage(
            state,
            class_dir,
            manifest,
            selected,
            specs,
            interleave=interleave,
            bundle=bundle,
            scene_prefix=scene_prefix,
        )

    vis_eps = sum(1 for s in step_trace if s.get("kind") == "visual" and s.get("episode_id"))
    math_eps = sum(1 for s in step_trace if s.get("kind") == "math" and s.get("episode_id"))

    sleep_rep: dict[str, Any] | None = None
    bridges_emergent = 0
    if sleep and (vis_eps or math_eps):
        sleep_rep = run_sleep(state, bundle)
        bridges_emergent = _emergent_bridge_count(sleep_rep)

    report: dict[str, Any] = {
        "store_id": store_dir.name,
        "class_id": manifest.get("class_id"),
        "class_dir": str(class_dir),
        "moment_id": moment_id or (stage_ids[0] if stage_ids else None),
        "stage_ids": list(stage_ids) if stage_ids else None,
        "interleave": interleave if not steps else "explicit_steps",
        "steps": len(step_trace),
        "visual_episodes": vis_eps,
        "math_episodes": math_eps,
        "step_trace": step_trace,
        "sleep": bool(sleep),
        "bridges_emergent": bridges_emergent,
        "token_counts": _token_counts(state),
    }
    if sleep_rep is not None:
        report["sleep_merged"] = len(sleep_rep.get("items") or [])

    report_file = report_path or (
        REPO_ROOT / "lab" / "visual-curriculum" / "generated" / "_ingest" / f"moment-{report['moment_id']}.json"
    )
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["report_path"] = str(report_file)

    if persist:
        mark_runtime_dirty(state)
        report["persist"] = save_runtime_state(
            store_dir,
            state,
            force=True,
            thin=True,
            sync_ltm_on_save=bool(sleep),
        )

    return report


def main() -> None:
    p = argparse.ArgumentParser(description="Ingest lesson moment (visual + math → one sleep)")
    p.add_argument("--store-dir", type=Path, default=None)
    p.add_argument("--class-dir", type=Path, default=REPO_ROOT / "lessons/visual-cards")
    p.add_argument("--manifest", default="class.manifest.json")
    p.add_argument("--moment-id", default=None)
    p.add_argument("--stage", nargs="+", default=None, dest="stage_ids")
    p.add_argument("--steps-json", type=Path, default=None, help="JSON file with steps[]")
    p.add_argument("--math-json", type=Path, default=None, help="JSON file with math_episodes[]")
    p.add_argument(
        "--interleave",
        choices=("after_each_visual", "after_all_visual"),
        default="after_each_visual",
    )
    p.add_argument("--no-sleep", action="store_true")
    p.add_argument("--no-persist", action="store_true")
    args = p.parse_args()

    steps = json.loads(args.steps_json.read_text(encoding="utf-8")) if args.steps_json else None
    math_eps = (
        json.loads(args.math_json.read_text(encoding="utf-8")) if args.math_json else None
    )

    rep = ingest_lesson_moment(
        args.store_dir or default_agent_store(),
        args.class_dir,
        manifest_name=args.manifest,
        moment_id=args.moment_id,
        steps=steps,
        stage_ids=args.stage_ids,
        math_episodes=math_eps,
        interleave=args.interleave,
        sleep=not args.no_sleep,
        persist=not args.no_persist,
    )
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
