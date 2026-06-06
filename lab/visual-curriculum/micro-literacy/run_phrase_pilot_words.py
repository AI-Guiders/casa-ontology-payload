#!/usr/bin/env python3
"""Phrase pilot: R1 analytic breakdown for phrase-event words (ADR-0033 closure).

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

_REPO = _CURRICULUM.parents[1]
_WORDLIST = _REPO / "lessons" / "literacy-cards" / "data" / "phrase-pilot-words-v1.txt"


def _slugs_from_wordlist() -> list[str]:
    from runner_infra import class_dir_for, import_tools_module

    build = import_tools_module(class_dir_for(LITERACY) / "tools", "build_word_cards")
    slugs: list[str] = []
    for ln in _WORDLIST.read_text(encoding="utf-8").splitlines():
        w = ln.strip()
        if w:
            slugs.append(build.slug_for_surface(w))
    return slugs


def main() -> None:
    from literacy_lab_io import analytic_entries_for_slugs, slugs_from_phrase_events
    from run_analytic_breakdown_pilot import run_analytic_breakdown

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--slug", action="append", default=[], help="Override slug list")
    p.add_argument("--phrase-p1", action="store_true", help="All phrase-event slugs")
    p.add_argument("--wordlist", action="store_true", help="Slugs from phrase-pilot-words-v1.txt")
    args = p.parse_args()

    if args.slug:
        slugs = [str(s) for s in args.slug]
    elif args.phrase_p1:
        slugs = slugs_from_phrase_events()
    elif args.wordlist:
        slugs = _slugs_from_wordlist()
    else:
        slugs = slugs_from_phrase_events()

    entries = analytic_entries_for_slugs(slugs)
    if not entries:
        raise SystemExit(f"no corpus entries for slugs: {slugs}")

    lab = lab_session(LITERACY, micro_dir=_MICRO)
    lab.run_main(
        lambda s: run_analytic_breakdown(s, entries, pilot="phrase-pilot-words"),
        summary_file="summary-phrase-pilot-words.json",
        summary_builder=lambda s: {"moments": s.summary_rows, "pilot": "phrase-pilot-words", "slugs": slugs},
    )


if __name__ == "__main__":
    main()
