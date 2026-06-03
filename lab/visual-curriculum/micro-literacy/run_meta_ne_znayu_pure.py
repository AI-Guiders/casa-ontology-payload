#!/usr/bin/env python3
"""Чистый мета «не знаю»: lex_only и phrase_vis, без кадров букв (уровень 1 — карточка ↔ concept)."""

from __future__ import annotations

import argparse
from pathlib import Path

import _ensure_paths  # noqa: F401

from lab_paths import setup_lab_paths

_REPO, _ = setup_lab_paths(__file__)
from curriculum_lab import CurriculumLabSession, IngestJob
from literacy_steps import lex_step

CONCEPT_ID = "lang.meta.epistemic.unknown"
FRAME_ID = "word-ne_znayu-sans"
SURFACE = "не знаю"
SLUG = "epistemic-unknown"
_LITERACY = _REPO / "lessons" / "literacy-cards"


def _schedule(rounds: int, modes: tuple[str, ...]) -> list[IngestJob]:
    jobs: list[IngestJob] = []
    for r in range(1, rounds + 1):
        if "lex_only" in modes:
            jobs.append(
                IngestJob(
                    f"lex-meta-pure-{SLUG}-lex-r{r}",
                    [lex_step(SURFACE, CONCEPT_ID, cue=SURFACE)],
                    {"mode": "lex_only"},
                )
            )
        if "phrase_vis" in modes:
            jobs.append(
                IngestJob(
                    f"lex-meta-pure-{SLUG}-vis-r{r}",
                    [{"visual_frame": FRAME_ID}, lex_step(SURFACE, CONCEPT_ID, cue=SURFACE)],
                    {"mode": "phrase_vis"},
                )
            )
    return jobs


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--rounds", type=int, default=6)
    p.add_argument(
        "--modes",
        nargs="*",
        default=["lex_only", "phrase_vis"],
        choices=["lex_only", "phrase_vis"],
    )
    args = p.parse_args()
    jobs = _schedule(args.rounds, tuple(args.modes))

    lab = CurriculumLabSession(
        class_dir=_LITERACY,
        generated_subdir="micro-literacy",
        extra_sys_paths=(_LITERACY / "tools",),
    )

    def _run(session: CurriculumLabSession) -> None:
        session.log({"concept": CONCEPT_ID, "moments": len(jobs)})
        session.run_jobs(jobs)

    lab.run_main(_run, summary_file="summary-meta-ne-znayu-pure.json")


if __name__ == "__main__":
    main()
