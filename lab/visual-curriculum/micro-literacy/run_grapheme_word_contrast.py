#!/usr/bin/env python3
"""Contrast pass: буква ↔ слово — чередование granule, отдельный sleep на пару."""

from __future__ import annotations

from pathlib import Path

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, bootstrap, cli_run_jobs, jobs_json_alternation

bootstrap(__file__)
_STEPS = Path(__file__).resolve().parent
ROUND_STEPS = (
    ("lex-granule-letter-a-lower.json", "letter"),
    ("lex-granule-word-mama.json", "word"),
    ("lex-granule-letter-a-upper.json", "letter"),
    ("lex-granule-word-kot.json", "word"),
)
ROUNDS = 3


def main() -> None:
    cli_run_jobs(
        LITERACY,
        lambda: jobs_json_alternation(
            _STEPS,
            ROUND_STEPS,
            rounds=ROUNDS,
            moment_id_fmt="lex-granule-contrast-r{round}-{stem}",
        ),
        summary_file="summary-grapheme-word-contrast.json",
        description=__doc__,
        log_start={"rounds": ROUNDS},
        summary_builder=lambda s: {"rounds": ROUNDS, "moments": s.summary_rows},
        micro_dir=_STEPS,
    )


if __name__ == "__main__":
    main()
