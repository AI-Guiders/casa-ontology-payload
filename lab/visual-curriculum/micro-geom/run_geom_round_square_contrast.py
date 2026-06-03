#!/usr/bin/env python3
"""Contrast pass: круг ↔ квадрат — каждый шаг свой sleep."""

from __future__ import annotations

from pathlib import Path

import _ensure_paths  # noqa: F401
from runner_infra import VISUAL, bootstrap, cli_json_batch

bootstrap(__file__)
_STEPS = Path(__file__).resolve().parent
MICRO = [("geom-micro-square-r7", "geom-micro-square.json")]


def main() -> None:
    cli_json_batch(VISUAL, _STEPS, MICRO, summary_file="summary-round-square-contrast.json", description=__doc__)


if __name__ == "__main__":
    main()
