#!/usr/bin/env python3
"""Phased visual-cards curriculum: ingest one stage → agent wake quanta → report.

Teacher drops cards stage-by-stage; agent life runs between stages (Kolb, sleep, curiosity).
No manifest oracle for bridges — report only counts emergent_crosslink from sleep.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

from casa.cli.ingest_visual_class import ingest_visual_class
from casa.domain.visual_tract import LATTICE_V1_LUM
from casa.prisms.memory.agent_life import agent_wake
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.shared.store_boot import boot_store
from casa.prisms.shared.store_layout import default_agent_store
from casa.prisms.visual.bridge_math import predict_math_for_vis_cue
from casa.prisms.visual.bootstrap import ensure_prism_visual


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stage_frame_ids(manifest: dict, stage_id: str) -> list[str]:
    stages = {str(s.get("id") or ""): s for s in manifest.get("stages") or []}
    stage = stages.get(stage_id)
    if not stage:
        raise ValueError(f"unknown stage: {stage_id}")
    lesson_ids = set(str(x) for x in stage.get("lesson_ids") or [])
    return [
        str(f.get("id") or "")
        for f in manifest.get("frames") or []
        if str(f.get("lesson_id") or "") in lesson_ids
    ]


def _count_vis_math_edges(state: dict) -> int:
    lats = memory_lattices(state)
    lum = lats.get(LATTICE_V1_LUM) or {}
    n = 0
    for cell in lum.get("cells") or []:
        if not isinstance(cell, list):
            continue
        for tok in cell:
            if isinstance(tok, str) and tok.startswith("E:") and "|math." in tok:
                n += 1
    return n


def _probe_frames(state: dict, frame_ids: list[str], *, top_k: int = 5) -> dict[str, list]:
    out: dict[str, list] = {}
    for fid in frame_ids:
        cue = f"vis:{fid}"
        out[fid] = predict_math_for_vis_cue(state, cue, top_k=top_k)
    return out


def run_phased(
    store_dir: Path,
    class_dir: Path,
    *,
    stage_ids: list[str] | None = None,
    wake_quanta: int = 25,
    skip_ingest: bool = False,
    report_dir: Path | None = None,
) -> dict[str, Any]:
    store_dir = store_dir.resolve()
    class_dir = class_dir.resolve()
    manifest_path = class_dir / "class.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    all_stages = sorted(manifest.get("stages") or [], key=lambda s: int(s.get("order") or 0))
    if stage_ids:
        wanted = set(stage_ids)
        stages = [s for s in all_stages if str(s.get("id") or "") in wanted]
        if len(stages) != len(wanted):
            missing = wanted - {str(s.get("id") or "") for s in stages}
            raise ValueError(f"unknown stages: {sorted(missing)}")
    else:
        stages = all_stages

    report_dir = (report_dir or REPO_ROOT / "lab" / "visual-curriculum" / "reports").resolve()
    report_dir.mkdir(parents=True, exist_ok=True)

    run_report: dict[str, Any] = {
        "started_at": _utc_now(),
        "store_dir": str(store_dir),
        "class_id": manifest.get("class_id"),
        "wake_quanta_per_stage": wake_quanta,
        "stages": [],
    }

    for stage in stages:
        sid = str(stage.get("id") or "")
        title = str(stage.get("title") or sid)
        frame_ids = _stage_frame_ids(manifest, sid)
        stage_rep: dict[str, Any] = {
            "stage_id": sid,
            "title": title,
            "frame_ids": frame_ids,
        }

        if not skip_ingest:
            ingest_rep = ingest_visual_class(
                store_dir,
                class_dir,
                stage_ids=[sid],
                sleep_after_stage=True,
                sleep_after_each=False,
                persist=True,
            )
            stage_rep["ingest"] = {
                "frames": ingest_rep.get("frames"),
                "bridges_emergent": ingest_rep.get("bridges_emergent"),
                "sleep_runs": ingest_rep.get("sleep_runs"),
                "s2a_ready": ingest_rep.get("s2a_ready"),
            }

        life_rep = agent_wake(store_dir, stop_after=max(1, wake_quanta), persist=True)
        stage_rep["life"] = {
            "quanta": life_rep.get("quanta_this_wake"),
            "macro_ticks": life_rep.get("macro_ticks"),
            "kolb_runs": (life_rep.get("self_drive") or {}).get("kolb_runs"),
            "last_self_drive": life_rep.get("last_self_drive"),
        }

        boot = boot_store(store_dir, prefer_field_state=True)
        state = ensure_prisms(boot["state"])
        ensure_prism_visual(state)
        stage_rep["bridges_total"] = _count_vis_math_edges(state)
        stage_rep["predict_vis_math"] = _probe_frames(state, frame_ids)

        out_path = report_dir / f"{sid}.json"
        out_path.write_text(json.dumps(stage_rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        stage_rep["report_path"] = str(out_path)
        run_report["stages"].append(stage_rep)
        print(json.dumps({"stage_done": sid, "bridges_total": stage_rep["bridges_total"]}, ensure_ascii=False), flush=True)

    run_report["finished_at"] = _utc_now()
    summary_path = report_dir / "run-summary.json"
    summary_path.write_text(json.dumps(run_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    run_report["summary_path"] = str(summary_path)
    return run_report


def main() -> None:
    p = argparse.ArgumentParser(description="Phased visual curriculum + agent wake between stages")
    p.add_argument("--store-dir", type=Path, default=None)
    p.add_argument("--class-dir", type=Path, default=REPO_ROOT / "lessons/visual-cards")
    p.add_argument("--stage", nargs="+", default=None, dest="stage_ids", help="Subset of stage ids")
    p.add_argument("--wake-quanta", type=int, default=25, help="Agent life quanta after each stage")
    p.add_argument("--skip-ingest", action="store_true", help="Only wake + probe (replay)")
    p.add_argument("--report-dir", type=Path, default=None)
    args = p.parse_args()

    rep = run_phased(
        args.store_dir or default_agent_store(root=REPO_ROOT),
        args.class_dir,
        stage_ids=args.stage_ids,
        wake_quanta=args.wake_quanta,
        skip_ingest=args.skip_ingest,
        report_dir=args.report_dir,
    )
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
