#!/usr/bin/env python3
"""Phrase P1 closure on von-neumann: corpus words → R1 breakdown → grammar meta pure."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import _ensure_paths  # noqa: F401

_REPO = Path(__file__).resolve().parents[3]
_TOOLS = _REPO / "lessons" / "literacy-cards" / "tools"
_MICRO = Path(__file__).resolve().parent
_CURRICULUM = _MICRO.parent


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=str(_REPO))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", default="von-neumann")
    p.add_argument("--skip-build", action="store_true")
    p.add_argument("--skip-ingest", action="store_true")
    p.add_argument("--skip-grammar", action="store_true")
    p.add_argument("--skip-probes", action="store_true")
    args = p.parse_args()

    py = sys.executable
    wordlist = _REPO / "lessons" / "literacy-cards" / "data" / "phrase-pilot-words-v1.txt"

    if not args.skip_build:
        _run([py, str(_TOOLS / "build_word_cards.py"), "--wordlist", str(wordlist), "--limit", "20"])
        _run([py, str(_TOOLS / "build_grammar_meta_cards.py"), "--case", "--agreement"])

    if not args.skip_ingest:
        _run([py, str(_MICRO / "run_phrase_pilot_words.py"), "--phrase-p1"])
        if not args.skip_grammar:
            for script in (
                "run_meta_grammar_person_pure.py",
                "run_meta_grammar_case_pure.py",
                "run_meta_grammar_agreement_pure.py",
            ):
                _run([py, str(_MICRO / script), "--rounds", "1", "--modes", "phrase_vis"])

    if not args.skip_probes:
        probes = [
            [py, str(_CURRICULUM / "probe_analytic_read_corpus.py"), "--store", args.store],
            [py, str(_CURRICULUM / "probe_phrase_compose_pilot.py"), "--store", args.store],
            [py, str(_CURRICULUM / "probe_phrase_permutation_equiv.py")],
            [py, str(_CURRICULUM / "probe_question_frame_pilot.py")],
            [py, str(_CURRICULUM / "probe_meta_grammar_person_quiz.py")],
            [py, str(_CURRICULUM / "probe_meta_grammar_agreement_quiz.py")],
            [py, str(_CURRICULUM / "probe_meta_grammar_case_quiz.py")],
        ]
        for cmd in probes:
            _run(cmd)


if __name__ == "__main__":
    main()
