#!/usr/bin/env python3
"""Контраст регистра lower↔upper для выбранных cue (без «a»), затем опционально a — подача."""

from __future__ import annotations

import argparse
from pathlib import Path

import _ensure_paths  # noqa: F401
from curriculum_lab import IngestJob, jobs_from_steps
from manifest_steps import frame_by_id, letter_frame_id, steps_for_frame
from runner_infra import LITERACY, bootstrap, class_dir_for, cli_lab_main, import_tools_module

bootstrap(__file__)
_MICRO = Path(__file__).resolve().parent
DEFAULT_CUES = ("b", "k", "o", "m", "t")
FINALE_CUE = "a"


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
                frame = frame_by_id(manifest, letter_frame_id(cue, register))
                steps = _enrich_steps(steps_for_frame(frame), lo, up, register, cue_slug=cue)
                items.append((f"lex-reg-{cue}-r{r}-{register}"[:80], steps))
    return jobs_from_steps(items)


def _parser(p: argparse.ArgumentParser) -> None:
    p.add_argument("--cues", nargs="*", default=list(DEFAULT_CUES))
    p.add_argument("--rounds", type=int, default=2, help="раундов lower↔upper на cue")
    p.add_argument("--finale-a-rounds", type=int, default=6, help="раундов для a после других (0=пропуск)")
    p.add_argument("--no-finale", action="store_true")


def _run(session, args: argparse.Namespace) -> None:
    cues = tuple(args.cues)
    build_letter_cards = import_tools_module(class_dir_for(LITERACY) / "tools", "build_letter_cards")
    manifest = session.load_manifest()
    jobs = _schedule(manifest, cues, rounds_per_cue=args.rounds, tools_cyrillic=build_letter_cards.CYRILLIC)
    if not args.no_finale and args.finale_a_rounds > 0:
        jobs.extend(
            _schedule(
                manifest,
                (FINALE_CUE,),
                rounds_per_cue=args.finale_a_rounds,
                tools_cyrillic=build_letter_cards.CYRILLIC,
            )
        )
    session.log({"cues": cues, "moments": len(jobs), "finale_a": not args.no_finale})
    session.run_jobs(jobs)


def main() -> None:
    cli_lab_main(
        LITERACY,
        _run,
        summary_file="summary-register-contrast-cues.json",
        description=__doc__,
        parser_setup=_parser,
        summary_builder=lambda s, args: {"cues": list(args.cues), "moments": s.summary_rows},
        micro_dir=_MICRO,
    )


if __name__ == "__main__":
    main()
