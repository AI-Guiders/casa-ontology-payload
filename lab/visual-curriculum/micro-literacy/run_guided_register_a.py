#!/usr/bin/env python3
"""Guided attention (text): vis + метаслово + grapheme в одном moment → один sleep."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from lab_paths import setup_lab_paths

_REPO, _ = setup_lab_paths(__file__)
from curriculum_lab import CurriculumLabSession, jobs_from_json_files
from pathlib import Path

_STEPS = Path(__file__).resolve().parent
_LITERACY = _REPO / "lessons" / "literacy-cards"
ROUNDS = 4
ROUND_FILES = (
    ("lex-guided-a-lower.json", "lower"),
    ("lex-guided-a-upper.json", "upper"),
)


def _schedule() -> list[tuple[str, str, dict]]:
    out: list[tuple[str, str, dict]] = []
    for r in range(1, ROUNDS + 1):
        for fname, tag in ROUND_FILES:
            out.append((f"lex-guided-a-r{r}-{tag}"[:80], fname, {"tag": tag}))
    return out


def main() -> None:
    jobs = jobs_from_json_files(_STEPS, _schedule())
    lab = CurriculumLabSession(class_dir=_LITERACY, reports_subdir="micro-literacy")
    lab.run_main(lambda s: s.run_jobs(jobs), summary_file="summary-guided-register-a.json")


if __name__ == "__main__":
    main()
