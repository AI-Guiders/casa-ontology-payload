#!/usr/bin/env python3
"""Phrase pilot B2: R1 analytic breakdown for «мыла», «раму» (ADR-0033 closure).

Закрывает W1 для phrase compose **после** stage-05 слогов в LTM:
  syllable chain → corpus word (lesson-06), без ingest analytic-probe-*.

Дальше: probe_analytic_read_corpus → probe_phrase_compose_pilot.
"""

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

_PHRASE_P1_EXTRA = ("27dae5010f7e", "c6eebd8384e6")


def main() -> None:
    from literacy_lab_io import analytic_entries_for_slugs
    from run_analytic_breakdown_pilot import run_analytic_breakdown

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--slug", action="append", default=[], help="Override slug list")
    args = p.parse_args()
    slugs = [str(s) for s in args.slug] if args.slug else list(_PHRASE_P1_EXTRA)
    entries = analytic_entries_for_slugs(slugs)
    lab = lab_session(LITERACY, micro_dir=_MICRO)
    lab.run_main(
        lambda s: run_analytic_breakdown(s, entries, pilot="phrase-pilot-words"),
        summary_file="summary-phrase-pilot-words.json",
        summary_builder=lambda s: {"moments": s.summary_rows, "pilot": "phrase-pilot-words"},
    )


if __name__ == "__main__":
    main()
