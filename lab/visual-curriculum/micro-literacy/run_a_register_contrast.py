#!/usr/bin/env python3
"""Contrast pass: а ↔ А — чередование register, отдельный sleep на пару."""

from __future__ import annotations

from pathlib import Path

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, bootstrap, cli_run_jobs, jobs_json_round_pairs

bootstrap(__file__)
_STEPS = Path(__file__).resolve().parent
ROUNDS = 8
_PAIRS = (
    ("lower", "lex-micro-a-lower.json"),
    ("upper", "lex-micro-a-upper.json"),
)


def main() -> None:
    cli_run_jobs(
        LITERACY,
        lambda: jobs_json_round_pairs(
            _STEPS,
            _PAIRS,
            rounds=ROUNDS,
            moment_id_fmt="lex-micro-a-contrast-r{round}-{tag}",
        ),
        summary_file="summary-a-register-contrast.json",
        description=__doc__,
        log_start={"rounds": ROUNDS},
        micro_dir=_STEPS,
    )


if __name__ == "__main__":
    main()
