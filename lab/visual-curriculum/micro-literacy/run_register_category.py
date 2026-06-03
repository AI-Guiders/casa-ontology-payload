#!/usr/bin/env python3
"""Категория регистра: letterCase — имена + exemplar по разным cue (Б/б, В/в, …)."""

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

FACE = "sans"
CATEGORIES = (
    (LETTER_CASE_UPPER, ("заглавная буква", "буква верхнего регистра"), "upper"),
    (LETTER_CASE_LOWER, ("строчная буква", "буква нижнего регистра"), "lower"),
)
DEFAULT_EXEMPLAR_CUES = ("b", "v")


def _exemplar_frame(cue: str, register: str) -> str:
    return f"letter-{cue}-{register}-{FACE}"


def _jobs(cues: tuple[str, ...], *, names_rounds: int, exemplar_rounds: int) -> list[IngestJob]:
    out: list[IngestJob] = []
    for concept_id, surfaces, register in CATEGORIES:
        reg = concept_id.rsplit(".", 1)[-1]
        for r in range(1, names_rounds + 1):
            mid = f"lex-cat-{reg}-names-r{r}"
            out.append(
                IngestJob(
                    mid,
                    [lex_step(s, concept_id) for s in surfaces],
                    {"concept_id": concept_id, "kind": "names", "cue": None},
                )
            )
        for cue in cues:
            exemplar_fid = _exemplar_frame(cue, register)
            for r in range(1, exemplar_rounds + 1):
                mid = f"lex-cat-{reg}-exemplar-{cue}-r{r}"
                steps = [{"visual_frame": exemplar_fid}]
                steps.extend(lex_step(s, concept_id) for s in surfaces)
                out.append(
                    IngestJob(
                        mid,
                        steps,
                        {
                            "concept_id": concept_id,
                            "kind": "exemplar",
                            "cue": cue,
                            "frame_id": exemplar_fid,
                        },
                    )
                )
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--exemplar-cues", nargs="*", default=list(DEFAULT_EXEMPLAR_CUES))
    p.add_argument("--names-rounds", type=int, default=0)
    p.add_argument("--exemplar-rounds", type=int, default=3)
    p.add_argument("--include-a", action="store_true")
    args = p.parse_args()

    cues = tuple(args.exemplar_cues)
    if args.include_a and "a" not in cues:
        cues = (*cues, "a")

    lab = CurriculumLabSession(
        class_dir=_LITERACY,
        generated_subdir="micro-literacy",
        extra_sys_paths=(_LITERACY / "tools",),
    )
    schedule = _jobs(cues, names_rounds=args.names_rounds, exemplar_rounds=args.exemplar_rounds)

    def _run(session: CurriculumLabSession) -> None:
        session.log({"exemplar_cues": cues, "names_rounds": args.names_rounds, "moments": len(schedule)})
        session.run_jobs(schedule)

    lab.run_main(
        _run,
        summary_file="summary-register-category.json",
        summary_builder=lambda s: {"exemplar_cues": cues, "moments": s.summary_rows},
    )


if __name__ == "__main__":
    main()
