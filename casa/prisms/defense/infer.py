#!/usr/bin/env python3
"""Defense life-event inference from dialogue (ADR-0076 P20a)."""

from __future__ import annotations

import re

CAREGIVER_TOKENS = (
    "отец",
    "отца",
    "отцу",
    "мать",
    "матер",
    "маме",
    "мама",
    "папа",
    "родител",
    "опекун",
    "caregiver",
)

VIOLENCE_TOKENS = (
    "душил",
    "душит",
    "удуш",
    "задыха",
    "не мог дыш",
    "не могла дыш",
    "ударил",
    "ударила",
    "бьёт",
    "бил",
    "била",
    "избил",
    "избила",
    "насил",
    "убил",
    "убила",
    "убьёт",
    "угрож",
    "пинал",
    "пинала",
    "избив",
)

THREAT_ONLY_TOKENS = (
    "напал",
    "напала",
    "насилие",
    "опасн",
    "угроза жизн",
    "чуть не убил",
    "чуть не убила",
)


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(tok in text for tok in tokens)


def infer_trauma_life_event(
    partner_text: str,
    *,
    subject_reply: str = "",
    query_intent: str = "",
) -> str | None:
    """Infer security_threat or caregiver_violation — operator cannot set."""
    del query_intent
    blob = f"{partner_text or ''} {subject_reply or ''}".strip().lower()
    if not blob:
        return None
    if _contains_any(blob, CAREGIVER_TOKENS) and _contains_any(blob, VIOLENCE_TOKENS):
        return "caregiver_violation"
    if _contains_any(blob, VIOLENCE_TOKENS) or _contains_any(blob, THREAT_ONLY_TOKENS):
        return "security_threat"
    if re.search(r"\b(страх|ужас|паник)\b", blob) and re.search(
        r"\b(дом|ночь|закрыл|запер|бежать)\b", blob
    ):
        return "security_threat"
    return None
