#!/usr/bin/env python3
"""Ingest -> probe -> reinforce (lab) по ADR-0030. Ядро sleep не трогаем."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import _ensure_paths  # noqa: F401

_CURRICULUM = Path(__file__).resolve().parents[1]
if str(_CURRICULUM) not in sys.path:
    sys.path.insert(0, str(_CURRICULUM))

from literacy_pedagogy import (  # noqa: E402
    STAGE_PROBE_SPECS,
    default_wordlist_for_stage,
    frames_for_stage,
    hippo_pending_surface_episodes,
    probe_issues,
    promote_emergent_routes_after_probe,
    reinforce_from_probe_report,
    run_probe_script,
    surface_from_frame,
)
from manifest_steps import steps_for_frame  # noqa: E402
from runner_infra import LITERACY, bootstrap, lab_session  # noqa: E402

bootstrap(__file__)
_MICRO = Path(__file__).resolve().parent


def _parser(p: argparse.ArgumentParser) -> None:
    p.add_argument("--stage", required=True)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument(
        "--order",
        choices=("wordlist", "frame_id", "manifest"),
        default="wordlist",
        help="wordlist = порядок файла (канон для closed-class); frame_id = сортировка id",
    )
    p.add_argument("--wordlist", type=Path, default=None)
    p.add_argument("--ingest-only", action="store_true")
    p.add_argument("--probe-only", action="store_true")
    p.add_argument("--skip-ingest", action="store_true")
    p.add_argument("--skip-probe", action="store_true")
    p.add_argument("--reinforce-tail", action="store_true", help="reinforce empty/ambiguous из probe")
    p.add_argument("--reinforce-copies", type=int, default=12)


def _run(session, args: argparse.Namespace) -> None:
    manifest = session.load_manifest()
    wordlist = args.wordlist
    if wordlist is None and args.order == "wordlist":
        wordlist = default_wordlist_for_stage(args.stage)

    frames = frames_for_stage(
        manifest,
        args.stage,
        limit=args.limit,
        offset=args.offset,
        order=args.order,
        wordlist_path=wordlist,
    )
    pending_before = hippo_pending_surface_episodes(session.state)
    session.log(
        {
            "pedagogy": "start",
            "stage": args.stage,
            "frames": len(frames),
            "order": args.order,
            "wordlist": str(wordlist) if wordlist else None,
            "hippo_pending_lex": len(pending_before),
            "note": "stop reactor before batch; one writer per store",
        }
    )
    if pending_before:
        session.log(
            {
                "warn": "hippo_has_pending",
                "count": len(pending_before),
                "scenes": [str(e.get("scene") or "")[:80] for e in pending_before[:5]],
            }
        )

    if not args.skip_ingest and not args.probe_only:
        for i, frame in enumerate(frames):
            fid = str(frame.get("id"))
            session.ingest(
                f"lex-{args.stage}-{fid}"[:80],
                steps_for_frame(frame),
                i=i + 1,
                frame_id=fid,
                surface=surface_from_frame(frame),
            )
            if (i + 1) % 10 == 0 or i + 1 == len(frames):
                session.log(session.summary_rows[-1])

    report: dict | None = None
    spec = STAGE_PROBE_SPECS.get(args.stage)
    issues: list[dict] = []
    if not args.skip_probe and not args.ingest_only:
        spec = STAGE_PROBE_SPECS.get(args.stage)
        if spec is None:
            raise SystemExit(f"no probe script for stage {args.stage!r}; add to teacher_pedagogy")
        report = run_probe_script(spec.script, extra_args=list(spec.extra_args))
        issues = probe_issues(report)
        session.log(
            {
                "probe": report.get("probe"),
                "gate_kind": report.get("gate_kind"),
                "know": report.get("know"),
                "ambiguous": report.get("ambiguous"),
                "empty": report.get("empty"),
                "wrong": report.get("wrong"),
                "total": report.get("total"),
                "issues": len(issues),
            }
        )
        promote = promote_emergent_routes_after_probe(session.state, report)
        if promote.get("promoted_count") or promote.get("passed"):
            session.log({"emergent_promote": promote})

    if (
        args.reinforce_tail
        and report is not None
        and issues
        and spec is not None
        and spec.reinforce_tail
    ):
        reinforced = reinforce_from_probe_report(
            session.state,
            report,
            copies=args.reinforce_copies,
        )
        session.log({"reinforce_tail": reinforced})
        report2 = run_probe_script(spec.script, extra_args=list(spec.extra_args))
        session.log(
            {
                "probe_after_reinforce": {
                    "know": report2.get("know"),
                    "ambiguous": report2.get("ambiguous"),
                    "empty": report2.get("empty"),
                    "total": report2.get("total"),
                }
            }
        )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    _parser(p)
    args = p.parse_args()
    lab = lab_session(LITERACY, micro_dir=_MICRO)
    lab.run_main(
        lambda s: _run(s, args),
        summary_file=f"summary-pedagogy-{args.stage}.json",
        summary_builder=lambda s: {"stage": args.stage, "moments": s.summary_rows},
    )


if __name__ == "__main__":
    main()
