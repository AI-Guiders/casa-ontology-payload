#!/usr/bin/env python3
"""L2 числительное + существительное: классы one / few / many (ADR-0033)."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import (
    LITERACY,
    PureMetaPhrase,
    bootstrap,
    class_dir_for,
    cli_rounds_modes_jobs,
    import_tools_module,
    jobs_pure_meta,
)

bootstrap(__file__)
meta = import_tools_module(class_dir_for(LITERACY) / "tools", "meta_concepts")

NUMERAL_PURE: tuple[PureMetaPhrase, ...] = tuple(
    PureMetaPhrase(
        concept_id=cid,
        surface=surface,
        frame_id=f"word-{slug}-sans",
        slug=slug,
    )
    for slug, surface, cid in (
        *meta.GRAMMAR_NUMERAL_CLASS_CARDS,
        *meta.GRAMMAR_NUMERAL_PHRASE_CARDS,
    )
)


def main() -> None:
    cli_rounds_modes_jobs(
        LITERACY,
        lambda rounds, modes: jobs_pure_meta(
            NUMERAL_PURE,
            rounds=rounds,
            modes=modes,
            moment_prefix="lex-grammar-numeral-pure",
        ),
        summary_file="summary-meta-grammar-numeral-pure.json",
        description=__doc__,
        summary_builder=lambda s, rounds, modes: {
            "modes": list(modes),
            "rounds": rounds,
            "numeral_cards": len(NUMERAL_PURE),
            "moments": s.summary_rows,
        },
    )


if __name__ == "__main__":
    main()
