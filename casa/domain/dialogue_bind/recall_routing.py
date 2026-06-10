#!/usr/bin/env python3
"""Journal-backed recall routing — /remember without «на поле …» (recommendations №5)."""

from __future__ import annotations

from pathlib import Path

from casa.domain.dialogue_bind.blocks import score_text
from casa.domain.dialogue_bind.journal import journal_recall_records

_RECALL_CUE_SUBSTRINGS = (
    "напомни",
    "напомин",
    "ты говорил",
    "мы говорили",
    "ты записал",
    "ты помнишь",
    "что ты знаешь",
    "что знаешь про",
    "мы договорили",
    "что ты про это",
    "ты учил",
)

_TEACH_TAGS = frozenset({"chat", "correction", "remember", "teach"})


def _taught_row(row: dict) -> bool:
    tags = {str(t).lower() for t in (row.get("tags") or [])}
    return bool(tags & _TEACH_TAGS)


def journal_recall_tract_boost(
    store_dir: Path | None,
    query: str,
    *,
    state: dict | None = None,
) -> tuple[int, int, list[str]]:
    """Boost recall/explain tracts when journal remembers partner teachings."""
    if store_dir is None:
        return 0, 0, []
    q = (query or "").strip()
    if not q:
        return 0, 0, []
    ql = q.lower()
    sources: list[str] = []
    recall_boost = 0
    explain_boost = 0

    for cue in _RECALL_CUE_SUBSTRINGS:
        if cue in ql:
            recall_boost += 30
            sources.append(f"recall_cue:{cue}")
            break

    rows = journal_recall_records(store_dir, q, limit=6, state=state)
    best_overlap = 0
    taught_hit = False
    for row in rows:
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        overlap = score_text(q, text, base=0)
        best_overlap = max(best_overlap, overlap)
        if overlap >= 6:
            row_boost = 38 if _taught_row(row) else 26
            recall_boost = max(recall_boost, row_boost)
            if _taught_row(row):
                taught_hit = True
            sources.append("journal:overlap")

    if taught_hit and best_overlap >= 4:
        recall_boost = max(recall_boost, 32)
        sources.append("journal:taught_tag")

    if recall_boost >= 24:
        explain_boost = max(explain_boost, recall_boost - 10)
        sources.append("journal:explain_shadow")

    return recall_boost, explain_boost, sources


def should_prefer_recall_intent(
    store_dir: Path | None,
    query: str,
    *,
    social_score: int = 0,
    state: dict | None = None,
) -> bool:
    recall_boost, _, _ = journal_recall_tract_boost(store_dir, query, state=state)
    if recall_boost < 28:
        return False
    # Journal overlap wins over raw social geometry even if phatic KB lit briefly.
    return recall_boost + 8 >= max(0, int(social_score))
