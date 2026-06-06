#!/usr/bin/env python3
"""Ingest -> probe -> reinforce for visual-cards stages (teacher framework)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import _ensure_paths  # noqa: F401

_CURRICULUM = Path(__file__).resolve().parents[1]
if str(_CURRICULUM) not in sys.path:
    sys.path.insert(0, str(_CURRICULUM))

from literacy_pedagogy import (  # noqa: E402
    VISUAL_STAGE_PROBES,
    hippo_pending_surface_episodes,
    probe_issues,
    promote_emergent_routes_after_probe,
    reinforce_from_probe_report,
    run_probe_script,
    surface_from_frame,
)
from manifest_steps import steps_for_frame  # noqa: E402
from runner_infra import VISUAL, bootstrap, lab_session  # noqa: E402
from teacher_pedagogy import load_class_manifest, stage_probe_for  # noqa: E402

bootstrap(__file__)
_MICRO = Path(__file__).resolve().parent
_CLASS_REL = "lessons/visual-cards"


def _frames_for_stage(stage_id: str, *, limit: int, offset: int) -> list[dict]:
    manifest = load_class_manifest(_CLASS_REL)
    lesson_ids: set[str] = set()
    for st in manifest.get("stages") or []:
        if str(st.get("id")) == stage_id:
            lesson_ids = set(st.get("lesson_ids") or [])
            break
    if not lesson_ids:
        raise SystemExit(f"unknown stage: {stage_id!r}")
    frames = [f for f in manifest.get("frames") or [] if str(f.get("lesson_id")) in lesson_ids]
    frames.sort(key=lambda f: str(f.get("id")))
    if offset:
        frames = frames[offset:]
    if limit > 0:
        frames = frames[:limit]
    return frames


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", required=True)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--ingest-only", action="store_true")
    p.add_argument("--probe-only", action="store_true")
    p.add_argument("--skip-ingest", action="store_true")
    p.add_argument("--skip-probe", action="store_true")
    p.add_argument("--reinforce-tail", action="store_true")
    p.add_argument("--reinforce-copies", type=int, default=12)
    args = p.parse_args()

    spec = stage_probe_for(_CLASS_REL, args.stage) or VISUAL_STAGE_PROBES.get(args.stage)
    if spec is None:
        raise SystemExit(f"no probe for visual stage {args.stage!r}")

    frames = _frames_for_stage(args.stage, limit=args.limit, offset=args.offset)
    lab = lab_session(VISUAL, micro_dir=_MICRO)

    def _run(session) -> None:
        pending_before = hippo_pending_surface_episodes(session.state)
        session.log(
            {
                "pedagogy": "start",
                "class": "visual-cards",
                "stage": args.stage,
                "frames": len(frames),
                "probe_script": spec.script,
                "gate_kind": spec.gate_kind.value,
                "hippo_pending_lex": len(pending_before),
            }
        )

        if not args.skip_ingest and not args.probe_only:
            for i, frame in enumerate(frames):
                fid = str(frame.get("id"))
                session.ingest(
                    f"vis-{args.stage}-{fid}"[:80],
                    steps_for_frame(frame),
                    i=i + 1,
                    frame_id=fid,
                    surface=surface_from_frame(frame),
                )

        report = None
        issues: list[dict] = []
        if not args.skip_probe and not args.ingest_only:
            report = run_probe_script(spec.script, extra_args=list(spec.extra_args))
            issues = probe_issues(report)
            session.log(
                {
                    "probe": report.get("probe"),
                    "gate_kind": report.get("gate_kind"),
                    "know": report.get("know"),
                    "total": report.get("total"),
                    "issues": len(issues),
                }
            )
            promote = promote_emergent_routes_after_probe(session.state, report)
            if promote.get("passed"):
                session.log({"emergent_promote": promote})

        if args.reinforce_tail and report and issues and spec.reinforce_tail:
            reinforced = reinforce_from_probe_report(
                session.state,
                report,
                copies=args.reinforce_copies,
            )
            session.log({"reinforce_tail": reinforced})

    lab.run_main(
        lambda s: _run(s),
        summary_file=f"summary-visual-pedagogy-{args.stage}.json",
        summary_builder=lambda s: {"stage": args.stage, "moments": s.summary_rows},
    )


if __name__ == "__main__":
    main()
