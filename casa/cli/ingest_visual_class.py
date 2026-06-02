#!/usr/bin/env python3
"""Ingest visual-cards class — imprint only; bridges emerge on sleep / agent choice."""

from __future__ import annotations

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path
from typing import Any

from casa.domain.prism_ids import PRISM_VISUAL
from casa.domain.prism_wire import prism_block
from casa.domain.visual_tract import VISUAL_LATTICE_IDS
from casa.prisms.memory.memory_prisms import ensure_prisms, run_sleep
from casa.cli.ingest_state import resolve_ingest_state
from casa.prisms.shared.store_layout import default_agent_store
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state
from casa.prisms.visual.bootstrap import ensure_prism_visual
from casa.prisms.visual.imprint import imprint_visual_frame
from casa.sensory.load_rgb_frame import load_rgb_frame


def _token_counts(state: dict) -> dict[str, int]:
    lats = prism_block(state, PRISM_VISUAL).get("lattices") or {}
    out: dict[str, int] = {}
    for lid in VISUAL_LATTICE_IDS:
        cells = (lats.get(lid) or {}).get("cells") or []
        out[lid] = sum(len(c) for c in cells)
    return out


def _lesson_ids_for_stages(manifest: dict, stage_ids: list[str]) -> list[str]:
    stages = {str(s.get("id") or ""): s for s in manifest.get("stages") or []}
    lesson_ids: list[str] = []
    for sid in stage_ids:
        stage = stages.get(sid)
        if not stage:
            raise ValueError(f"unknown stage: {sid}")
        for lid in stage.get("lesson_ids") or []:
            if lid not in lesson_ids:
                lesson_ids.append(str(lid))
    return lesson_ids


def _lesson_to_stage(manifest: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for stage in manifest.get("stages") or []:
        sid = str(stage.get("id") or "")
        for lid in stage.get("lesson_ids") or []:
            out[str(lid)] = sid
    return out


def _stage_order(manifest: dict) -> list[str]:
    stages = sorted(manifest.get("stages") or [], key=lambda s: int(s.get("order") or 0))
    return [str(s.get("id") or "") for s in stages]


def _group_frames_by_stage(manifest: dict, selected: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    l2s = _lesson_to_stage(manifest)
    buckets: dict[str, list[dict[str, Any]]] = {}
    for frame in selected:
        sid = l2s.get(str(frame.get("lesson_id") or ""), "_ungrouped")
        buckets.setdefault(sid, []).append(frame)
    groups: list[tuple[str, list[dict[str, Any]]]] = []
    for sid in _stage_order(manifest):
        if sid in buckets:
            groups.append((sid, buckets.pop(sid)))
    for sid, frames in buckets.items():
        groups.append((sid, frames))
    return groups


def _emergent_crosslink_count(sleep_rep: dict[str, Any]) -> int:
    return sum(
        1 for item in sleep_rep.get("items") or [] if item.get("kind") == "emergent_crosslink"
    )


def ingest_visual_class(
    store_dir: Path,
    class_dir: Path,
    *,
    manifest_name: str = "class.manifest.json",
    lesson_ids: list[str] | None = None,
    stage_ids: list[str] | None = None,
    frame_ids: list[str] | None = None,
    sleep_after_stage: bool = True,
    sleep_after_each: bool = False,
    persist: bool = True,
    state: dict | None = None,
) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    class_dir = class_dir.resolve()
    manifest_path = class_dir / manifest_name
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    filter_lessons: set[str] | None = None
    if stage_ids:
        filter_lessons = set(_lesson_ids_for_stages(manifest, stage_ids))
    if lesson_ids:
        ids = set(lesson_ids)
        filter_lessons = ids if filter_lessons is None else filter_lessons & ids
    filter_frames = set(frame_ids) if frame_ids else None

    frames = list(manifest.get("frames") or [])
    selected: list[dict[str, Any]] = []
    for frame in frames:
        fid = str(frame.get("id") or "")
        lid = str(frame.get("lesson_id") or "")
        if filter_lessons is not None and lid not in filter_lessons:
            continue
        if filter_frames is not None and fid not in filter_frames:
            continue
        selected.append(frame)

    if not selected:
        raise ValueError("no frames matched lesson/stage/frame filter")

    state = resolve_ingest_state(store_dir, state)
    state["store"]["last_class"] = manifest.get("class_id")

    ensure_prism_visual(state)
    frames_report: list[dict[str, Any]] = []
    stages_report: list[dict[str, Any]] = []
    sleep_runs = 0
    bridges_emergent = 0

    stage_groups = _group_frames_by_stage(manifest, selected)

    for stage_id, stage_frames in stage_groups:
        stage_episodes = 0
        stage_emergent = 0

        for frame in stage_frames:
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
            if rep.get("episode_id"):
                stage_episodes += 1

            frame_emergent = 0
            if sleep_after_each and rep.get("episode_id"):
                sleep_rep = run_sleep(state, None)
                frame_emergent = _emergent_crosslink_count(sleep_rep)
                sleep_runs += 1
                bridges_emergent += frame_emergent
                stage_emergent += frame_emergent

            frames_report.append(
                {
                    "id": frame.get("id"),
                    "path": str(rel).replace("\\", "/"),
                    "scene_label": frame.get("scene_label"),
                    "curriculum_tags": frame.get("curriculum_tags"),
                    "stage_id": stage_id,
                    "emergent_crosslinks": frame_emergent,
                    **rep,
                }
            )

        if sleep_after_stage and not sleep_after_each and stage_episodes > 0:
            sleep_rep = run_sleep(state, None)
            stage_emergent = _emergent_crosslink_count(sleep_rep)
            sleep_runs += 1
            bridges_emergent += stage_emergent

        if stage_frames:
            stages_report.append(
                {
                    "stage_id": stage_id,
                    "frames": len(stage_frames),
                    "episodes": stage_episodes,
                    "emergent_crosslinks": stage_emergent,
                }
            )

    token_counts = _token_counts(state)
    ready = all(token_counts.get(lid, 0) > 0 for lid in VISUAL_LATTICE_IDS)

    sleep_mode = "after_each_frame" if sleep_after_each else ("after_stage" if sleep_after_stage else "none")

    report: dict[str, Any] = {
        "store_id": store_dir.name,
        "class_id": manifest.get("class_id"),
        "class_dir": str(class_dir),
        "lesson_filter": sorted(filter_lessons) if filter_lessons else None,
        "stage_filter": list(stage_ids) if stage_ids else None,
        "frame_filter": list(filter_frames) if filter_frames else None,
        "sleep_mode": sleep_mode,
        "frames": len(frames_report),
        "frames_report": frames_report,
        "stages_report": stages_report,
        "token_counts": token_counts,
        "s2a_ready": ready,
        "sleep_runs": sleep_runs,
        "bridges_emergent": bridges_emergent,
    }

    if persist:
        mark_runtime_dirty(state)
        persist_rep = save_runtime_state(
            store_dir,
            state,
            force=True,
            thin=True,
            sync_ltm_on_save=bool(sleep_runs),
        )
        report["persist"] = {
            "saved": bool(persist_rep.get("saved")),
            "field_version": persist_rep.get("field_version") or state.get("field_version"),
            "tier": persist_rep.get("tier"),
        }
        (class_dir / "last-ingest-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return report


def main() -> None:
    p = argparse.ArgumentParser(description="Ingest visual-cards (imprint; emergent bridges)")
    p.add_argument("--store-dir", type=Path, default=None)
    p.add_argument("--class-dir", type=Path, default=REPO_ROOT / "lessons/visual-cards")
    p.add_argument("--manifest", default="class.manifest.json")
    p.add_argument("--lesson-ids", nargs="+", default=None)
    p.add_argument("--stage", nargs="+", default=None, dest="stage_ids")
    p.add_argument("--frame-ids", nargs="+", default=None)
    p.add_argument(
        "--sleep-after-each-frame",
        action="store_true",
        help="Sleep after every frame (legacy; default is once per stage)",
    )
    p.add_argument("--no-sleep", action="store_true")
    p.add_argument("--no-persist", action="store_true")
    args = p.parse_args()

    rep = ingest_visual_class(
        args.store_dir or default_agent_store(),
        args.class_dir,
        manifest_name=args.manifest,
        lesson_ids=args.lesson_ids,
        stage_ids=args.stage_ids,
        frame_ids=args.frame_ids,
        sleep_after_stage=not args.no_sleep and not args.sleep_after_each_frame,
        sleep_after_each=args.sleep_after_each_frame and not args.no_sleep,
        persist=not args.no_persist,
    )
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
