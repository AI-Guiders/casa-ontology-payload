#!/usr/bin/env python3
"""Block pedagogy runner — wave ingest + held-out gate (generic)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import _ensure_paths  # noqa: F401

_CURRICULUM = Path(__file__).resolve().parents[1]
if str(_CURRICULUM) not in sys.path:
    sys.path.insert(0, str(_CURRICULUM))

from block_pedagogy import (  # noqa: E402
    all_wave_jobs,
    block_kind,
    load_block_spec,
    phrase_wave_event_ids,
)
from literacy_pedagogy import (  # noqa: E402
    hippo_pending_surface_episodes,
    ingest_probe_failure_frames,
    probe_issues,
    promote_emergent_routes_after_probe,
    reinforce_from_probe_report,
    run_probe_script,
)
from runner_infra import LITERACY, bootstrap, lab_session  # noqa: E402

bootstrap(__file__)
_MICRO = Path(__file__).resolve().parent


def _parser(p: argparse.ArgumentParser) -> None:
    p.add_argument("--block", default="block-01-grapheme-cyrl")
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--spec", type=Path, default=None)
    p.add_argument("--wave", type=int, action="append", default=[])
    p.add_argument("--ingest-only", action="store_true")
    p.add_argument("--probe-only", action="store_true")
    p.add_argument("--skip-ingest", action="store_true")
    p.add_argument("--skip-probe", action="store_true")
    p.add_argument("--reinforce-tail", action="store_true")
    p.add_argument("--reinforce-copies", type=int, default=12)
    p.add_argument("--reinforce-ingest-copies", type=int, default=3)
    p.add_argument("--no-reinforce-ingest", action="store_true")


def _bootstrap_block(session, block_id: str) -> None:
    if block_id == "block-09c-morphemics-cyrl":
        from casa.prisms.memory.bootstrap_morph_role_ru import bootstrap_morph_role_lattice

        rep = bootstrap_morph_role_lattice(session.store_dir, session.state, persist=True)
        session.log({"bootstrap": "morph-role-ru", **rep})


def _ingest_phrase_waves(session, spec: dict, *, waves: list[int] | None) -> None:
    from phrase_self_drive_core import run_phrase_self_drive_event

    event_ids = phrase_wave_event_ids(spec, waves=waves)
    session.log({"phrase_ingest": "start", "events": event_ids})
    for i, eid in enumerate(event_ids, start=1):
        goal = f"goal.read.phrase#{eid}"
        row = run_phrase_self_drive_event(session.store_dir, session.state, goal=goal)
        session.log({"phrase_event": eid, "wake_complete": row.get("wake_complete"), "i": i})


def _run(session, args: argparse.Namespace) -> None:
    spec = load_block_spec(args.spec, block_id=args.block)
    block_id = str(spec.get("block_id") or args.block)
    kind = block_kind(spec)
    waves = args.wave or None
    pending_before = hippo_pending_surface_episodes(session.state)
    jobs = all_wave_jobs(spec, waves=waves) if kind != "phrase" else []
    session.log(
        {
            "pedagogy": "block-start",
            "block": block_id,
            "kind": kind,
            "moments": len(jobs) if kind != "phrase" else len(phrase_wave_event_ids(spec, waves=waves)),
            "waves": waves or "all",
            "hippo_pending_lex": len(pending_before),
        }
    )

    if not args.skip_ingest and not args.probe_only:
        _bootstrap_block(session, block_id)
        if kind == "phrase":
            _ingest_phrase_waves(session, spec, waves=waves)
        else:
            for i, (mid, steps) in enumerate(jobs):
                session.ingest(mid, steps, i=i + 1)
                if (i + 1) % 20 == 0 or i + 1 == len(jobs):
                    session.log(session.summary_rows[-1])
            session.save(sync_ltm=False)

    report: dict | None = None
    issues: list[dict] = []
    if not args.skip_probe and not args.ingest_only:
        report = run_probe_script(
            "probe_block_held_out.py",
            extra_args=["--block", block_id, "--store", args.store],
            allow_gate_fail=args.reinforce_tail,
        )
        if kind != "phrase":
            issues = probe_issues(report)
        session.log(
            {
                "probe": report.get("probe"),
                "gate_pass": report.get("gate_pass"),
                "know": report.get("know") or report.get("phrase_know_count"),
                "total": report.get("total") or report.get("total_events"),
                "issues": len(issues),
            }
        )
        promote = promote_emergent_routes_after_probe(session.state, report)
        if promote.get("promoted_count") or promote.get("passed"):
            session.log({"emergent_promote": promote})

    if args.reinforce_tail and report is not None and issues:
        if kind != "phrase" and not args.no_reinforce_ingest:
            ingested = ingest_probe_failure_frames(
                session,
                spec,
                report,
                moment_copies=args.reinforce_ingest_copies,
            )
            session.log({"reinforce_ingest": ingested})
        reinforced = reinforce_from_probe_report(session.state, report, copies=args.reinforce_copies)
        session.log({"reinforce_tail": reinforced})
        session.save(sync_ltm=False)
        report2 = run_probe_script(
            "probe_block_held_out.py",
            extra_args=["--block", block_id, "--store", args.store],
            allow_gate_fail=True,
        )
        session.log(
            {
                "probe_after_reinforce": {
                    "know": report2.get("know"),
                    "total": report2.get("total"),
                    "gate_pass": report2.get("gate_pass"),
                }
            }
        )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    _parser(p)
    args = p.parse_args()
    block_id = args.block
    lab = lab_session(LITERACY, micro_dir=_MICRO, store_id=args.store)
    lab.run_main(
        lambda s: _run(s, args),
        summary_file=f"summary-{block_id}-pedagogy.json",
        summary_builder=lambda s: {"block": block_id, "moments": s.summary_rows},
    )


if __name__ == "__main__":
    main()
