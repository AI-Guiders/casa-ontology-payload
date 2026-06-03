#!/usr/bin/env python3
"""Literacy pilot: а/А + мама/кот/дом (отдельный sleep на moment)."""

from __future__ import annotations

from pathlib import Path

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, bootstrap, cli_json_batch

bootstrap(__file__)
_STEPS = Path(__file__).resolve().parent
MICRO = [
    ("lex-micro-a-lower", "lex-micro-a-lower.json"),
    ("lex-micro-a-upper", "lex-micro-a-upper.json"),
    ("lex-micro-word-mama", "lex-micro-word-mama.json"),
    ("lex-micro-word-kot", "lex-micro-word-kot.json"),
    ("lex-micro-word-dom", "lex-micro-word-dom.json"),
]


def main() -> None:
    cli_json_batch(LITERACY, _STEPS, MICRO, summary_file="summary-pilot-literacy-start.json", description=__doc__)


if __name__ == "__main__":
    main()
