#!/usr/bin/env python3
"""Literacy r2: повтор moment'ов (min_lex_votes=2 для emergent)."""

from __future__ import annotations

from pathlib import Path

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, bootstrap, cli_json_batch

bootstrap(__file__)
_STEPS = Path(__file__).resolve().parent
MICRO = [
    ("lex-micro-a-lower-r2", "lex-micro-a-lower.json"),
    ("lex-micro-a-upper-r2", "lex-micro-a-upper.json"),
    ("lex-micro-word-mama-r2", "lex-micro-word-mama.json"),
    ("lex-micro-word-kot-r2", "lex-micro-word-kot.json"),
    ("lex-micro-word-dom-r2", "lex-micro-word-dom.json"),
]


def main() -> None:
    cli_json_batch(LITERACY, _STEPS, MICRO, summary_file="summary-pilot-literacy-r2.json", description=__doc__)


if __name__ == "__main__":
    main()
