#!/usr/bin/env python3
"""Категория регистра: letterCase — имена + exemplar по разным cue (Б/б, В/в, …)."""

from __future__ import annotations

import argparse

import _ensure_paths  # noqa: F401
from runner_infra import (
    LITERACY,
    bootstrap,
    class_dir_for,
    cli_lab_main,
    import_tools_module,
    jobs_register_category,
)

bootstrap(__file__)
meta = import_tools_module(class_dir_for(LITERACY) / "tools", "meta_concepts")
CATEGORIES = (
    (meta.LETTER_CASE_UPPER, ("заглавная буква", "буква верхнего регистра"), "upper"),
    (meta.LETTER_CASE_LOWER, ("строчная буква", "буква нижнего регистра"), "lower"),
)
DEFAULT_EXEMPLAR_CUES = ("b", "v")


def _parser(p: argparse.ArgumentParser) -> None:
    p.add_argument("--exemplar-cues", nargs="*", default=list(DEFAULT_EXEMPLAR_CUES))
    p.add_argument("--names-rounds", type=int, default=0)
    p.add_argument("--exemplar-rounds", type=int, default=3)
    p.add_argument("--include-a", action="store_true")


def _run(session, args: argparse.Namespace) -> None:
    cues = tuple(args.exemplar_cues)
    if args.include_a and "a" not in cues:
        cues = (*cues, "a")
    schedule = jobs_register_category(
        CATEGORIES,
        exemplar_cues=cues,
        names_rounds=args.names_rounds,
        exemplar_rounds=args.exemplar_rounds,
    )
    session.log({"exemplar_cues": cues, "names_rounds": args.names_rounds, "moments": len(schedule)})
    session.run_jobs(schedule)


def main() -> None:
    cli_lab_main(
        LITERACY,
        _run,
        summary_file="summary-register-category.json",
        description=__doc__,
        parser_setup=_parser,
        summary_builder=lambda s, args: {"exemplar_cues": list(args.exemplar_cues), "moments": s.summary_rows},
    )


if __name__ == "__main__":
    main()
