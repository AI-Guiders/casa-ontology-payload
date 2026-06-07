#!/usr/bin/env python3
"""Block 9b pedagogy — passage journal ingest + probe_passage_comprehend_ru_v0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import _ensure_paths  # noqa: F401

_CURRICULUM = Path(__file__).resolve().parents[1]
if str(_CURRICULUM) not in sys.path:
    sys.path.insert(0, str(_CURRICULUM))

from passage_pedagogy import ingest_passage_moments, load_passage_cases  # noqa: E402
from runner_infra import LITERACY, bootstrap, lab_session  # noqa: E402

bootstrap(__file__)
_MICRO = Path(__file__).resolve().parent


def _parser(p: argparse.ArgumentParser) -> None:
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--pilot", type=Path, default=None)
    p.add_argument("--copies", type=int, default=2)
    p.add_argument("--ingest-only", action="store_true")
    p.add_argument("--probe-only", action="store_true")
    p.add_argument("--skip-ingest", action="store_true")


def _run(session, args: argparse.Namespace) -> None:
    cases = load_passage_cases(args.pilot)
    session.log({"pedagogy": "passage-9b-start", "cases": len(cases), "store": args.store})

    if not args.skip_ingest and not args.probe_only:
        reps = ingest_passage_moments(
            session.store_dir,
            session.state,
            cases=cases,
            copies=args.copies,
        )
        session.log({"passage_ingest": "done", "remembered": sum(1 for r in reps if r.get("remembered"))})

    if args.ingest_only:
        return

    from probe_passage_comprehend_ru_v0 import _run as run_probe

    report = run_probe(store_id=args.store)
    passed = int(report.get("know") or 0) == int(report.get("total") or 0) and report.get("total")
    session.log(
        {
            "probe": "probe_passage_comprehend_ru_v0",
            "know": report.get("know"),
            "total": report.get("total"),
            "gate_pass": passed,
        }
    )
    if not passed:
        session.log({"passage_9b": "red", "items": report.get("items")})
        raise SystemExit(1)


def main() -> None:
    p = argparse.ArgumentParser(description="Block 9b passage pedagogy")
    _parser(p)
    args = p.parse_args()
    lab = lab_session(LITERACY, micro_dir=_MICRO, store_id=args.store)
    lab.run_main(
        lambda s: _run(s, args),
        summary_file="summary-passage-9b-pedagogy.json",
        summary_builder=lambda s: {"block": "passage-9b", "rows": s.summary_rows},
    )


if __name__ == "__main__":
    main()
