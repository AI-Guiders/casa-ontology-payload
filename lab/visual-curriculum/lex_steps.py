"""Шаг moment с lexical (vis↔lex): literacy-cards, visual-cards+meta, …"""

from __future__ import annotations

from typing import Any


def lex_step(
    surface: str,
    concept_id: str,
    *,
    cue: str | None = None,
    lattice_id: str = "lexicon-ru",
) -> dict[str, Any]:
    cid = str(concept_id)
    return {
        "lexical": {
            "cue": cue if cue is not None else cid.rsplit(".", 1)[-1],
            "correct": surface,
            "concept_id": cid,
            "lattice_id": lattice_id,
        }
    }
