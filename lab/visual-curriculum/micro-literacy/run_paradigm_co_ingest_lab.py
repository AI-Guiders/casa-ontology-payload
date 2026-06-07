#!/usr/bin/env python3
"""W5 paradigm co-ingest: analytic breakdown for pilot slug sets (step 4)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, bootstrap, lab_session

bootstrap(__file__)
_MICRO = Path(__file__).resolve().parent
_CURRICULUM = _MICRO.parent
if str(_CURRICULUM) not in sys.path:
    sys.path.insert(0, str(_CURRICULUM))


def _pilot_slugs() -> list[str]:
    from casa.prisms.visual.paradigm_ltm import PILOT_PARADIGM_SLUG_SETS

    out: list[str] = []
    for slug_set in PILOT_PARADIGM_SLUG_SETS:
        out.extend(sorted(slug_set))
    return list(dict.fromkeys(out))


def main() -> None:
    from literacy_lab_io import analytic_entries_for_slugs
    from run_analytic_breakdown_pilot import run_analytic_breakdown

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--slug", action="append", default=[], help="Override slug list")
    args = p.parse_args()

    slugs = [str(s) for s in args.slug] if args.slug else _pilot_slugs()
    entries = analytic_entries_for_slugs(slugs)
    missing = [s for s in slugs if s not in {e.get("slug") for e in entries}]
    if missing:
        raise SystemExit(f"no corpus entries for slugs: {missing}")

    lab = lab_session(LITERACY, micro_dir=_MICRO)
    lab.run_main(
        lambda s: run_analytic_breakdown(s, entries, pilot="paradigm-co-ingest"),
        summary_file="summary-paradigm-co-ingest.json",
        summary_builder=lambda s: {
            "moments": s.summary_rows,
            "pilot": "paradigm-co-ingest",
            "slugs": slugs,
        },
    )


if __name__ == "__main__":
    main()
