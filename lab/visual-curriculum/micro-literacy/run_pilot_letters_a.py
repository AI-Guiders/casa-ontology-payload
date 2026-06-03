#!/usr/bin/env python3
"""Pilot: а / А — два micro-moment (отдельный sleep каждый)."""

from __future__ import annotations

from pathlib import Path

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, bootstrap, cli_json_batch

bootstrap(__file__)
_STEPS = Path(__file__).resolve().parent
MICRO = [
    ("lex-micro-a-lower", "lex-micro-a-lower.json"),
    ("lex-micro-a-upper", "lex-micro-a-upper.json"),
]


def main() -> None:
    cli_json_batch(LITERACY, _STEPS, MICRO, summary_file="summary-pilot-a.json", description=__doc__)


if __name__ == "__main__":
    main()
