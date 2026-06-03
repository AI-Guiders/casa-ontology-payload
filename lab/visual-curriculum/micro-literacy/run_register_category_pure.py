#!/usr/bin/env python3
"""Чистая категория регистра: без grapheme-кадров букв в moment."""

from __future__ import annotations

import argparse
from pathlib import Path

import _ensure_paths  # noqa: F401

from lab_paths import setup_lab_paths

_REPO, _ = setup_lab_paths(__file__)
from curriculum_lab import CurriculumLabSession, IngestJob
from literacy_steps import lex_step

_LITERACY = _REPO / "lessons" / "literacy-cards"
_TOOLS = _LITERACY / "tools"
import sys

if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
from meta_concepts import LETTER_CASE_LOWER, LETTER_CASE_UPPER  # noqa: E402
PHRASES = (
    (LETTER_CASE_UPPER, "заглавная буква", "word-capital-zaglavnaya-bukva-sans", "zaglavnaya-bukva"),
    (LETTER_CASE_UPPER, "буква верхнего регистра", "word-capital-verhnego-registra-sans", "verhnego-registra"),
    (LETTER_CASE_LOWER, "строчная буква", "word-lowercase-strochnaya-bukva-sans", "strochnaya-bukva"),
    (LETTER_CASE_LOWER, "буква нижнего регистра", "word-lowercase-nizhnego-registra-sans", "nizhnego-registra"),
)


def _schedule(rounds: int, modes: tuple[str, ...]) -> list[IngestJob]:
    jobs: list[IngestJob] = []
    for r in range(1, rounds + 1):
        for concept_id, surface, frame_id, slug in PHRASES:
            reg = concept_id.rsplit(".", 1)[-1]
            if "lex_only" in modes:
                jobs.append(
                    IngestJob(
                        f"lex-cat-pure-{reg}-lex-{slug}-r{r}",
                        [lex_step(surface, concept_id)],
                        {"mode": "lex_only"},
                    )
                )
            if "phrase_vis" in modes:
                jobs.append(
                    IngestJob(
                        f"lex-cat-pure-{reg}-vis-{slug}-r{r}",
                        [{"visual_frame": frame_id}, lex_step(surface, concept_id)],
                        {"mode": "phrase_vis"},
                    )
                )
    return jobs


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--rounds", type=int, default=5)
    p.add_argument("--modes", nargs="*", default=["lex_only", "phrase_vis"], choices=["lex_only", "phrase_vis"])
    args = p.parse_args()
    jobs = _schedule(args.rounds, tuple(args.modes))

    lab = CurriculumLabSession(
        class_dir=_LITERACY,
        generated_subdir="micro-literacy",
        extra_sys_paths=(_LITERACY / "tools",),
    )

    def _run(session: CurriculumLabSession) -> None:
        session.log({"modes": args.modes, "rounds": args.rounds, "moments": len(jobs)})
        session.run_jobs(jobs)

    lab.run_main(
        _run,
        summary_file="summary-register-category-pure.json",
        summary_builder=lambda s: {"modes": list(args.modes), "rounds": args.rounds, "moments": s.summary_rows},
    )


if __name__ == "__main__":
    main()
