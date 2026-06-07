"""Block dict helpers and journal text markers."""

from __future__ import annotations

import re
from typing import Any

from casa.prisms.control.sn_cen_runtime import AnswerBlock

JOURNAL_BOOTSTRAP_MARKERS = (
    "это мой журнал",
    "я — нейманн",
    "я - нейманн",
)
WAKE_JOURNAL_MARKERS = (
    "проснулся",
    "agent-self-default",
    "lattice ready",
)


def tokenize(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"[\w\u0400-\u04FF]+", text, flags=re.UNICODE) if len(w) > 2]


def score_text(query: str, text: str, *, base: int = 0) -> int:
    score = base
    tl = text.lower()
    for tok in tokenize(query):
        if tok in tl:
            score += 4
    return score


def block_dict(
    concept_id: str,
    text: str,
    *,
    source: str,
    score: int = 10,
    section: str = "",
    slots: dict[str, Any] | None = None,
) -> dict[str, Any]:
    t = str(text or "").strip()
    row: dict[str, Any] = {
        "concept_id": concept_id,
        "text": t,
        "section": section or source,
        "doc_path": source,
        "score": score,
        "source": source,
    }
    if slots:
        row["slots"] = dict(slots)
    return row


def answer_block_to_dict(b: AnswerBlock | dict[str, Any]) -> dict[str, Any]:
    if isinstance(b, dict):
        return dict(b)
    return block_dict(
        str(b.concept_id),
        str(b.text),
        source="cen",
        score=int(b.score),
        section=str(b.section or "cen"),
    )


def is_journal_bootstrap_text(text: str) -> bool:
    tl = str(text or "").lower()
    return any(m in tl for m in JOURNAL_BOOTSTRAP_MARKERS)


def is_wake_journal_text(text: str) -> bool:
    tl = str(text or "").lower()
    return any(m in tl for m in WAKE_JOURNAL_MARKERS)
