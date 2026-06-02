#!/usr/bin/env python3
"""Teacher session: reinforce count moments → quiz probe (no ML bench)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

from casa.cli.ingest_lesson_moment import ingest_lesson_moment
from casa.cli.ingest_state import resolve_ingest_state
from casa.prisms.shared.store_layout import default_agent_store
from casa.prisms.shared.store_lock import store_session_lock
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state
from casa.prisms.visual.bridge_math import predict_math_for_vis_cue, vis_frame_concept_id


# Orion: два контекста → один инвариант «два», один sleep
INVARIANT_TWO_STEPS: list[dict[str, Any]] = [
    {"visual_frame": "count-2-grains"},
    {"math": {"cue": "2", "correct": "2", "concept_id": "math.num.two", "scene": "invariant:two:grains"}},
    {"visual_frame": "count-2-cows"},
    {"math": {"cue": "2", "correct": "2", "concept_id": "math.num.two", "scene": "invariant:two:cows"}},
]

# Teacher reinforcement — три примера «смотри и число»
REINFORCE_STEPS: list[dict[str, Any]] = [
    {"visual_frame": "count-1-dot"},
    {"math": {"cue": "1", "correct": "1", "concept_id": "math.num.one", "scene": "reinforce:1"}},
    {"visual_frame": "count-2-dots"},
    {"math": {"cue": "2", "correct": "2", "concept_id": "math.num.two", "scene": "reinforce:2"}},
    {"visual_frame": "count-3-dots"},
    {"math": {"cue": "3", "correct": "3", "concept_id": "math.num.three", "scene": "reinforce:3"}},
]

# Quiz — другие картинки, учитель спрашивает «сколько?» через emergent bridge
QUIZ_FRAMES: list[dict[str, str]] = [
    {"frame_id": "count-2-grains", "teacher_note": "зёрна"},
    {"frame_id": "count-2-cows", "teacher_note": "коровы"},
    {"frame_id": "count-3-dots", "teacher_note": "три точки (видели в закреплении — проверка)"},
    {"frame_id": "count-2-shapes", "teacher_note": "два круга"},
    {"frame_id": "count-4-shapes", "teacher_note": "четыре прямоугольника"},
]

_EXPECT_HINTS: dict[str, str] = {
    "count-2-grains": "math.num.two",
    "count-2-cows": "math.num.two",
    "count-3-dots": "math.num.three",
    "count-2-shapes": "math.num.two",
    "count-4-shapes": "math.num.four",
}


def _probe(state: dict, frame_ids: list[str], *, top_k: int = 3) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for fid in frame_ids:
        preds = predict_math_for_vis_cue(state, fid, top_k=top_k)
        top = preds[0] if preds else None
        hint = _EXPECT_HINTS.get(fid)
        rows.append(
            {
                "frame_id": fid,
                "vis_cue": f"vis:{fid}",
                "vis_concept": vis_frame_concept_id(fid),
                "math_top": [{"concept_id": c, "score": s} for c, s in preds],
                "teacher_guess": top[0] if top else None,
                "teacher_hint": hint,
                "matches_hint": bool(top and hint and top[0] == hint),
            }
        )
    return {"items": rows, "matched": sum(1 for r in rows if r.get("matches_hint"))}


def run_teacher_count_session(
    store_dir: Path,
    *,
    class_dir: Path | None = None,
    persist: bool = True,
    skip_reinforce: bool = False,
    lesson: str = "reinforce",
) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    class_dir = (class_dir or (REPO_ROOT / "lessons/visual-cards")).resolve()
    report_dir = REPO_ROOT / "lab" / "visual-curriculum" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    with store_session_lock(store_dir, holder="teacher-count-session"):
        state = resolve_ingest_state(store_dir, None)

        quiz_ids = [str(q["frame_id"]) for q in QUIZ_FRAMES]
        before = _probe(state, quiz_ids)

        reinforce_rep: dict[str, Any] | None = None
        if not skip_reinforce:
            if lesson == "orion-invariant-two":
                steps = INVARIANT_TWO_STEPS
                moment_id = "teacher-orion-invariant-two"
            else:
                steps = REINFORCE_STEPS
                moment_id = "teacher-reinforce-count"
            reinforce_rep = ingest_lesson_moment(
                store_dir,
                class_dir,
                moment_id=moment_id,
                steps=steps,
                sleep=True,
                persist=False,
                state=state,
                report_path=report_dir / f"{moment_id}.json",
            )

        after = _probe(state, quiz_ids)

        report: dict[str, Any] = {
            "store_id": store_dir.name,
            "session": "teacher-count-quiz",
            "lesson": lesson,
            "reinforce": reinforce_rep,
            "quiz_frames": QUIZ_FRAMES,
            "before_reinforce": before,
            "after_reinforce": after,
        }

        out_path = report_dir / f"teacher-count-quiz-{lesson}.json"
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["report_path"] = str(out_path)

        if persist:
            mark_runtime_dirty(state)
            save_runtime_state(store_dir, state, force=True, thin=True, sync_ltm_on_save=True)

    return report


def main() -> None:
    p = argparse.ArgumentParser(description="Teacher: reinforce count → quiz probe")
    p.add_argument("--store-dir", type=Path, default=None)
    p.add_argument("--class-dir", type=Path, default=REPO_ROOT / "lessons/visual-cards")
    p.add_argument("--skip-reinforce", action="store_true", help="Probe only")
    p.add_argument(
        "--lesson",
        choices=("reinforce", "orion-invariant-two"),
        default="reinforce",
        help="Teacher moment before quiz",
    )
    p.add_argument("--no-persist", action="store_true")
    args = p.parse_args()

    rep = run_teacher_count_session(
        args.store_dir or default_agent_store(),
        class_dir=args.class_dir,
        persist=not args.no_persist,
        skip_reinforce=args.skip_reinforce,
        lesson=args.lesson,
    )
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
