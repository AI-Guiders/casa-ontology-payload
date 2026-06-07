"""Passage geometry and meaning graph (ADR-0053)."""

from __future__ import annotations

from casa.prisms.tick.passage.comprehend import (
    _RU_STOP,
    has_passage_context,
    passage_focus_question,
    passage_salient_lemmas,
    passage_sentence_bind_rows,
    passage_sentences,
    passage_tokens,
    sentence_overlap,
    split_passage_query,
)
from casa.prisms.tick.passage.meaning import (
    PropositionRow,
    extract_passage_meaning,
    proposition_bind_blocks,
    proposition_tract_boost,
)
from casa.prisms.tick.passage.priors import apply_journal_prior, dialogue_tract_prior

__all__ = [
    "PropositionRow",
    "_RU_STOP",
    "apply_journal_prior",
    "dialogue_tract_prior",
    "extract_passage_meaning",
    "has_passage_context",
    "passage_focus_question",
    "passage_salient_lemmas",
    "passage_sentence_bind_rows",
    "passage_sentences",
    "passage_tokens",
    "proposition_bind_blocks",
    "proposition_tract_boost",
    "sentence_overlap",
    "split_passage_query",
]
