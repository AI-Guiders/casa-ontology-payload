#!/usr/bin/env python3
"""Repeat visual curriculum as lesson_moment (visual + math → one sleep per stage)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

from casa.cli.ingest_lesson_moment import ingest_lesson_moment
from casa.cli.moment_plan import build_moment_steps, load_manifest, stage_ids_in_order
from casa.cli.ingest_state import resolve_ingest_state
from casa.prisms.shared.store_layout import default_agent_store
from casa.prisms.shared.store_lock import store_session_lock
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state


def run_moment_curriculum(
    store_dir: Path,
    class_dir: Path,
    *,
    stage_ids: list[str] | None = None,
    run_tag: str = "repeat-v2",
    persist: bool = True,
) -> dict:
    store_dir = store_dir.resolve()
    class_dir = class_dir.resolve()
    manifest = load_manifest(class_dir)
    stages = stage_ids or stage_ids_in_order(manifest)

    state = resolve_ingest_state(store_dir, None)
    reports_dir = REPO_ROOT / "lab" / "visual-curriculum" / "reports" / run_tag
    reports_dir.mkdir(parents=True, exist_ok=True)

    summary: list[dict] = []
    t0 = time.time()
    total_bridges = 0

    with store_session_lock(store_dir, holder=f"moment-curriculum:{run_tag}"):
        for i, sid in enumerate(stages):
            steps = build_moment_steps(manifest, sid)
            moment_id = f"{run_tag}-{sid}"
            t_stage = time.time()
            rep = ingest_lesson_moment(
                store_dir,
                class_dir,
                moment_id=moment_id,
                steps=steps,
                sleep=True,
                persist=False,
                state=state,
                report_path=reports_dir / f"{moment_id}.json",
            )
            bridges = int(rep.get("bridges_emergent") or 0)
            total_bridges += bridges
            row = {
                "stage_id": sid,
                "moment_id": moment_id,
                "visual_episodes": rep.get("visual_episodes"),
                "math_episodes": rep.get("math_episodes"),
                "bridges_emergent": bridges,
                "elapsed_s": round(time.time() - t_stage, 1),
            }
            summary.append(row)
            print(json.dumps({"stage_done": row}, ensure_ascii=False), flush=True)

        if persist:
            mark_runtime_dirty(state)
            save_runtime_state(store_dir, state, force=True, thin=True, sync_ltm_on_save=True)

    out = {
        "run_tag": run_tag,
        "store_id": store_dir.name,
        "stages": len(summary),
        "bridges_emergent_total": total_bridges,
        "elapsed_s": round(time.time() - t0, 1),
        "stages_report": summary,
        "reports_dir": str(reports_dir),
    }
    (reports_dir / "summary.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Repeat visual-cards as lesson_moment curriculum")
    p.add_argument("--store-dir", type=Path, default=None)
    p.add_argument("--class-dir", type=Path, default=REPO_ROOT / "lessons/visual-cards")
    p.add_argument("--stage", nargs="+", default=None, dest="stage_ids")
    p.add_argument("--run-tag", default="repeat-v2")
    p.add_argument("--no-persist", action="store_true")
    args = p.parse_args()

    rep = run_moment_curriculum(
        args.store_dir or default_agent_store(),
        args.class_dir,
        stage_ids=args.stage_ids,
        run_tag=args.run_tag,
        persist=not args.no_persist,
    )
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
