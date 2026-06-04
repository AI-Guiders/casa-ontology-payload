#!/usr/bin/env python3
"""Чистое мета-лицо: 1 vis + 1 lex → lang.meta.grammar.person.* (ADR-0030)."""

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

PERSON_PURE: tuple[PureMetaPhrase, ...] = tuple(
    PureMetaPhrase(
        concept_id=cid,
        surface=surface,
        frame_id=f"word-{slug}-sans",
        slug=slug,
    )
    for slug, surface, cid in meta.GRAMMAR_PERSON_CARDS
)


def main() -> None:
    cli_rounds_modes_jobs(
        LITERACY,
        lambda rounds, modes: jobs_pure_meta(
            PERSON_PURE,
            rounds=rounds,
            modes=modes,
            moment_prefix="lex-grammar-person-pure",
        ),
        summary_file="summary-meta-grammar-person-pure.json",
        description=__doc__,
        summary_builder=lambda s, rounds, modes: {
            "modes": list(modes),
            "rounds": rounds,
            "person_cards": len(PERSON_PURE),
            "moments": s.summary_rows,
        },
    )


if __name__ == "__main__":
    main()
