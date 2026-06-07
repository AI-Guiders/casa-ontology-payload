#!/usr/bin/env python3
"""Passage geometry for bind — tokens, sentences, overlap scores (no compose if-ladder)."""

from __future__ import annotations

import re

_RU_STOP = frozenset(
    {
        "она",
        "он",
        "они",
        "оно",
        "это",
        "в",
        "на",
        "и",
        "а",
        "но",
        "как",
        "по",
        "за",
        "из",
        "от",
        "до",
        "при",
        "для",
        "его",
        "её",
        "ее",
        "их",
        "ты",
        "вы",
        "мы",
        "не",
        "ни",
        "же",
        "ли",
        "бы",
        "уже",
        "ещё",
        "еще",
        "тот",
        "эта",
        "там",
        "тут",
        "весь",
        "вся",
        "все",
    }
)


def passage_focus_question(query: str) -> str:
    _, question = split_passage_query(query)
    return question or (query or "").strip()


def split_passage_query(query: str) -> tuple[str, str]:
    q = (query or "").strip()
    if not q:
        return "", ""
    parts = [p.strip() for p in re.split(r"\n\s*\n", q) if p.strip()]
    if len(parts) >= 2:
        return parts[0], parts[-1]
    return "", q


def has_passage_context(query: str) -> bool:
    passage, question = split_passage_query(query)
    return len(passage) >= 12 and len(question) >= 4


def passage_tokens(passage: str) -> set[str]:
    return {
        t.lower()
        for t in re.findall(r"[\w\u0400-\u04FF]+", passage, flags=re.UNICODE)
        if len(t) > 2 and t.lower() not in _RU_STOP
    }


def passage_sentences(passage: str) -> list[str]:
    raw = [s.strip() for s in re.split(r"(?<=[.!?…])\s+", passage.strip()) if s.strip()]
    if raw:
        return raw
    return [passage.strip()] if passage.strip() else []


def sentence_overlap(sentence: str, focus_tokens: set[str]) -> int:
    st = passage_tokens(sentence)
    return len(st & focus_tokens)


def passage_salient_lemmas(passage: str, question: str, *, limit: int = 14) -> list[str]:
    """Salient passage tokens for lattice co-placement (question overlap + frequency)."""
    focus = passage_tokens(question)
    counts: dict[str, int] = {}
    for sent in passage_sentences(passage):
        for tok in passage_tokens(sent):
            counts[tok] = counts.get(tok, 0) + 1
    ranked = sorted(
        counts.keys(),
        key=lambda w: (w in focus, counts[w], len(w)),
        reverse=True,
    )
    return ranked[:limit]


def passage_sentence_bind_rows(passage: str, question: str) -> list[tuple[int, str, int]]:
    """(index, sentence, bind_score) ranked for field co-placement — not compose routing."""
    focus = passage_tokens(question) | passage_tokens(passage)
    rows: list[tuple[int, str, int]] = []
    for i, sent in enumerate(passage_sentences(passage)):
        ov = sentence_overlap(sent, focus)
        score = 14 + ov * 8
        rows.append((i, sent, score))
    rows.sort(key=lambda row: row[2], reverse=True)
    return rows
