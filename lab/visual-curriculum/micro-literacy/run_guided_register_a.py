#!/usr/bin/env python3
"""Guided attention (text): vis + метаслово + grapheme в одном moment → один sleep."""

from __future__ import annotations

from pathlib import Path

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, bootstrap, cli_run_jobs, jobs_from_round_files

bootstrap(__file__)
_STEPS = Path(__file__).resolve().parent
ROUNDS = 4
ROUND_FILES = (
    ("lex-guided-a-lower.json", "lower"),
    ("lex-guided-a-upper.json", "upper"),
)


def main() -> None:
    cli_run_jobs(
        LITERACY,
        lambda: jobs_from_round_files(
            _STEPS,
            ROUND_FILES,
            rounds=ROUNDS,
            moment_id_fmt="lex-guided-a-r{round}-{tag}",
        ),
        summary_file="summary-guided-register-a.json",
        description=__doc__,
        micro_dir=_STEPS,
    )


if __name__ == "__main__":
    main()
