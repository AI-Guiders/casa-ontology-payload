#!/usr/bin/env python3
"""L3 согласование: phrase vis + lang.meta.grammar.agreement.* (ADR-0030)."""

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

AGREEMENT_PURE: tuple[PureMetaPhrase, ...] = tuple(
    PureMetaPhrase(
        concept_id=cid,
        surface=surface,
        frame_id=f"word-{slug}-sans",
        slug=slug,
    )
    for slug, surface, cid in meta.GRAMMAR_AGREEMENT_PHRASE_CARDS
)


def main() -> None:
    cli_rounds_modes_jobs(
        LITERACY,
        lambda rounds, modes: jobs_pure_meta(
            AGREEMENT_PURE,
            rounds=rounds,
            modes=modes,
            moment_prefix="lex-grammar-agreement-pure",
        ),
        summary_file="summary-meta-grammar-agreement-pure.json",
        description=__doc__,
        summary_builder=lambda s, rounds, modes: {
            "modes": list(modes),
            "rounds": rounds,
            "agreement_cards": len(AGREEMENT_PURE),
            "moments": s.summary_rows,
        },
    )


if __name__ == "__main__":
    main()
