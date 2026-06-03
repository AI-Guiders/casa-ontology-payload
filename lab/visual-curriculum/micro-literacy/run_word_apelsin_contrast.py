#!/usr/bin/env python3
"""Контраст целого слова: апельсин ↔ Апельсин (регистр на уровне слова)."""

from __future__ import annotations

from pathlib import Path

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, bootstrap, cli_run_jobs, jobs_from_round_files

bootstrap(__file__)
_STEPS = Path(__file__).resolve().parent
ROUNDS = 4
ROUND_FILES = (
    ("lex-micro-word-apelsin.json", "lower"),
    ("lex-micro-word-apelsin-cap.json", "cap"),
)


def main() -> None:
    cli_run_jobs(
        LITERACY,
        lambda: jobs_from_round_files(
            _STEPS,
            ROUND_FILES,
            rounds=ROUNDS,
            moment_id_fmt="lex-apelsin-contrast-r{round}-{tag}",
        ),
        summary_file="summary-word-apelsin-contrast.json",
        description=__doc__,
        micro_dir=_STEPS,
    )


if __name__ == "__main__":
    main()
