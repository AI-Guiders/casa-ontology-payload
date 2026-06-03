#!/usr/bin/env python3
"""Чистая категория регистра: без grapheme-кадров букв в moment."""

from __future__ import annotations

import _ensure_paths  # noqa: F401
from runner_infra import (
    LITERACY,
    bootstrap,
    class_dir_for,
    cli_rounds_modes_jobs,
    import_tools_module,
    jobs_register_category_pure,
)

bootstrap(__file__)
meta = import_tools_module(class_dir_for(LITERACY) / "tools", "meta_concepts")
PHRASES = (
    (meta.LETTER_CASE_UPPER, "заглавная буква", "word-capital-zaglavnaya-bukva-sans", "zaglavnaya-bukva"),
    (meta.LETTER_CASE_UPPER, "буква верхнего регистра", "word-capital-verhnego-registra-sans", "verhnego-registra"),
    (meta.LETTER_CASE_LOWER, "строчная буква", "word-lowercase-strochnaya-bukva-sans", "strochnaya-bukva"),
    (meta.LETTER_CASE_LOWER, "буква нижнего регистра", "word-lowercase-nizhnego-registra-sans", "nizhnego-registra"),
)


def main() -> None:
    cli_rounds_modes_jobs(
        LITERACY,
        lambda rounds, modes: jobs_register_category_pure(PHRASES, rounds=rounds, modes=modes),
        summary_file="summary-register-category-pure.json",
        description=__doc__,
        summary_builder=lambda s, rounds, modes: {
            "modes": list(modes),
            "rounds": rounds,
            "moments": s.summary_rows,
        },
    )


if __name__ == "__main__":
    main()
