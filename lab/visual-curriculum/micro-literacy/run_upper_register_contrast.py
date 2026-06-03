#!/usr/bin/env python3
"""Контраст только upper: чередование заглавных Б, В, … — один moment = один кадр + grapheme."""

from __future__ import annotations

import argparse

import _ensure_paths  # noqa: F401
from lab_paths import setup_lab_paths

_REPO, _ = setup_lab_paths(__file__)
from curriculum_lab import CurriculumLabSession, IngestJob, jobs_from_steps
from literacy_moment import steps_for_frame

_LITERACY = _REPO / "lessons" / "literacy-cards"
_MICRO = __import__("pathlib").Path(__file__).resolve().parent
DEFAULT_CUES = ("b", "v", "k", "m", "o", "t")
FACE = "sans"
REGISTER = "upper"


def _frame_for_cue(manifest: dict, cue: str) -> dict:
    fid = f"letter-{cue}-{REGISTER}-{FACE}"
    for f in manifest.get("frames") or []:
        if str(f.get("id")) == fid:
            return f
    raise KeyError(fid)


def _schedule(manifest: dict, cues: tuple[str, ...], *, rounds: int) -> list[IngestJob]:
    items: list[tuple[str, list[dict]]] = []
    for r in range(1, rounds + 1):
        for cue in cues:
            frame = _frame_for_cue(manifest, cue)
            items.append((f"lex-upper-contrast-{cue}-r{r}", steps_for_frame(frame)))
    return jobs_from_steps(items)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--cues", nargs="*", default=list(DEFAULT_CUES))
    p.add_argument("--rounds", type=int, default=2)
    args = p.parse_args()
    cues = tuple(args.cues)

    lab = CurriculumLabSession(
        class_dir=_LITERACY,
        generated_subdir="micro-literacy",
        extra_sys_paths=(_MICRO,),
    )

    def _run(session: CurriculumLabSession) -> None:
        manifest = session.load_manifest()
        jobs = _schedule(manifest, cues, rounds=args.rounds)
        session.log({"register": REGISTER, "cues": cues, "moments": len(jobs)})
        session.run_jobs(jobs)

    lab.run_main(
        _run,
        summary_file="summary-upper-register-contrast.json",
        summary_builder=lambda s: {"cues": list(cues), "register": REGISTER, "moments": s.summary_rows},
    )


if __name__ == "__main__":
    main()
