#!/usr/bin/env python3
"""Пилот метаязыка (text tract): буква, слово, заглавная, строчная."""

from __future__ import annotations

from pathlib import Path

import _ensure_paths  # noqa: F401
from runner_infra import LITERACY, bootstrap, cli_json_batch

bootstrap(__file__)
_STEPS = Path(__file__).resolve().parent
MICRO = [
    ("lex-meta-bukva", "lex-meta-bukva.json"),
    ("lex-meta-slovo", "lex-meta-slovo.json"),
    ("lex-meta-zaglavnaya", "lex-meta-zaglavnaya.json"),
    ("lex-meta-strochnaya", "lex-meta-strochnaya.json"),
]


def main() -> None:
    cli_json_batch(LITERACY, _STEPS, MICRO, summary_file="summary-meta-language.json", description=__doc__)


if __name__ == "__main__":
    main()
