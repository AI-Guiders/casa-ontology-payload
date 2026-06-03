#!/usr/bin/env python3
"""Контраст регистра lower↔upper для выбранных cue (без «a»), затем опционально a — подача."""

from __future__ import annotations

import argparse

import _ensure_paths  # noqa: F401
from lab_paths import setup_lab_paths

_REPO, _ = setup_lab_paths(__file__)
from curriculum_lab import CurriculumLabSession, IngestJob, jobs_from_steps
from literacy_moment import steps_for_frame

_LITERACY = _REPO / "lessons" / "literacy-cards"
_MICRO = __import__("pathlib").Path(__file__).resolve().parent
DEFAULT_CUES = ("b", "k", "o", "m", "t")
FINALE_CUE = "a"
FACE = "sans"


def _frame_for_cue(manifest: dict, cue: str, register: str) -> dict:
    fid = f"letter-{cue}-{register}-{FACE}"
    for f in manifest.get("frames") or []:
        if str(f.get("id")) == fid:
            return f
    raise KeyError(fid)


def _enrich_steps(
    steps: list[dict],
    lo_glyph: str,
    up_glyph: str,
    register: str,
    *,
    cue_slug: str,
) -> list[dict]:
    out = []
    for step in steps:
        if "lexical" not in step:
            out.append(step)
            continue
        spec = dict(step["lexical"])
        g = lo_glyph if register == "lower" else up_glyph
        spec["cue"] = f"{cue_slug}-{register}"
        spec["correct"] = f"буква {g}"
        out.append({"lexical": spec})
    return out


def _schedule(
    manifest: dict,
    cues: tuple[str, ...],
    *,
    rounds_per_cue: int,
    tools_cyrillic: list[tuple[str, str, str]],
) -> list[IngestJob]:
    glyph = {c: (lo, up) for c, lo, up in tools_cyrillic}
    items: list[tuple[str, list[dict]]] = []
    for cue in cues:
        lo, up = glyph[cue]
        for r in range(1, rounds_per_cue + 1):
            for register in ("lower", "upper"):
                frame = _frame_for_cue(manifest, cue, register)
                steps = _enrich_steps(steps_for_frame(frame), lo, up, register, cue_slug=cue)
                items.append((f"lex-reg-{cue}-r{r}-{register}"[:80], steps))
    return jobs_from_steps(items)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--cues", nargs="*", default=list(DEFAULT_CUES))
    p.add_argument("--rounds", type=int, default=2, help="раундов lower↔upper на cue")
    p.add_argument("--finale-a-rounds", type=int, default=6, help="раундов для a после других (0=пропуск)")
    p.add_argument("--no-finale", action="store_true")
    args = p.parse_args()
    cues = tuple(args.cues)

    lab = CurriculumLabSession(
        class_dir=_LITERACY,
        reports_subdir="micro-literacy",
        extra_sys_paths=(_LITERACY / "tools", _MICRO),
    )

    def _run(session: CurriculumLabSession) -> None:
        from build_letter_cards import CYRILLIC  # noqa: E402

        manifest = session.load_manifest()
        jobs = _schedule(manifest, cues, rounds_per_cue=args.rounds, tools_cyrillic=CYRILLIC)
        if not args.no_finale and args.finale_a_rounds > 0:
            jobs.extend(
                _schedule(
                    manifest,
                    (FINALE_CUE,),
                    rounds_per_cue=args.finale_a_rounds,
                    tools_cyrillic=CYRILLIC,
                )
            )
        session.log({"cues": cues, "moments": len(jobs), "finale_a": not args.no_finale})
        session.run_jobs(jobs)

    lab.run_main(
        _run,
        summary_file="summary-register-contrast-cues.json",
        summary_builder=lambda s: {"cues": list(cues), "moments": s.summary_rows},
    )


if __name__ == "__main__":
    main()
