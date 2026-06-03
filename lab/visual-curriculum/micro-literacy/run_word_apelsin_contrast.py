#!/usr/bin/env python3
"""Контраст целого слова: апельсин ↔ Апельсин (регистр на уровне слова)."""

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
    ("lex-micro-word-apelsin.json", "lower"),
    ("lex-micro-word-apelsin-cap.json", "cap"),
)


def _schedule() -> list[tuple[str, str, dict]]:
    out: list[tuple[str, str, dict]] = []
    for r in range(1, ROUNDS + 1):
        for fname, tag in ROUND_FILES:
            out.append((f"lex-apelsin-contrast-r{r}-{tag}"[:80], fname, {"tag": tag}))
    return out


def main() -> None:
    jobs = jobs_from_json_files(_STEPS, _schedule())
    lab = CurriculumLabSession(class_dir=_LITERACY, generated_subdir="micro-literacy")
    lab.run_main(lambda s: s.run_jobs(jobs), summary_file="summary-word-apelsin-contrast.json")


if __name__ == "__main__":
    main()
