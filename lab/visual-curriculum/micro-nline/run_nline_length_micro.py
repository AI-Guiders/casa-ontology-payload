#!/usr/bin/env python3
"""S4a: math.numberline.length на чистых кадрах lesson-22 (одна полоса 0→n)."""

from __future__ import annotations

from pathlib import Path

import _ensure_paths  # noqa: F401
from runner_infra import NLINE, bootstrap, cli_json_batch

bootstrap(__file__)
_STEPS = Path(__file__).resolve().parent
MICRO = [
    ("nline-length-pure-2-r1", "nline-length-pure-2.json"),
    ("nline-length-pure-3-r1", "nline-length-pure-3.json"),
]


def main() -> None:
    cli_json_batch(
        NLINE,
        _STEPS,
        MICRO,
        summary_file="summary-nline-length.json",
        description=__doc__,
        log_start={"stage": "S4a-math-numberline-length"},
    )


if __name__ == "__main__":
    main()
