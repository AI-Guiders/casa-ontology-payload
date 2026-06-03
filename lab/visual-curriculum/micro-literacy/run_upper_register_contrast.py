#!/usr/bin/env python3
"""Контраст только upper: чередование заглавных Б, В, … — один moment = один кадр + grapheme."""

from __future__ import annotations

import argparse
from pathlib import Path

import _ensure_paths  # noqa: F401
from manifest_steps import jobs_manifest_frame_rounds
from runner_infra import LITERACY, bootstrap, cli_lab_main

bootstrap(__file__)
_MICRO = Path(__file__).resolve().parent
DEFAULT_CUES = ("b", "v", "k", "m", "o", "t")
REGISTER = "upper"


def _parser(p: argparse.ArgumentParser) -> None:
    p.add_argument("--cues", nargs="*", default=list(DEFAULT_CUES))
    p.add_argument("--rounds", type=int, default=2)


def _run(session, args: argparse.Namespace) -> None:
    cues = tuple(args.cues)
    jobs = jobs_manifest_frame_rounds(
        session.load_manifest(),
        cues,
        register=REGISTER,
        rounds=args.rounds,
        moment_id_fmt="lex-upper-contrast-{cue}-r{round}",
    )
    session.log({"register": REGISTER, "cues": cues, "moments": len(jobs)})
    session.run_jobs(jobs)


def main() -> None:
    cli_lab_main(
        LITERACY,
        _run,
        summary_file="summary-upper-register-contrast.json",
        description=__doc__,
        parser_setup=_parser,
        summary_builder=lambda s, args: {"cues": list(args.cues), "register": REGISTER, "moments": s.summary_rows},
        micro_dir=_MICRO,
    )


if __name__ == "__main__":
    main()
