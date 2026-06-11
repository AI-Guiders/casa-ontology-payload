#!/usr/bin/env python3
"""Render discourse sketches to surface text."""

from __future__ import annotations

import re

from casa.prisms.tick.discourse.model import ClauseSketch, DiscourseSketch, PhraseSketch


def query_tokens(query: str) -> set[str]:
    return {
        t.lower()
        for t in re.findall(r"[\w\u0400-\u04FF]+", query, flags=re.UNICODE)
        if len(t) > 1
    }


def partner_turn_word_count(query: str) -> int:
    from casa.prisms.tick.passage import split_passage_query

    _, focus = split_passage_query(query)
    text = focus or query
    return len(re.findall(r"[\w\u0400-\u04FF]+", text, flags=re.UNICODE))


def partner_turn_is_brief(query: str, *, threshold: int = 6) -> bool:
    ql = (query or "").strip().lower()
    if any(m in ql for m in ("расскаж", "о себе", "представь", "представ")):
        return False
    return partner_turn_word_count(query) <= threshold


def closing_for_query(_query: str) -> str:
    return "."


def capitalize_sentence(text: str) -> str:
    t = text.strip()
    if not t:
        return t
    return t[0].upper() + t[1:]


def render_clause(clause: ClauseSketch) -> str:
    parts = [p.strip() for p in clause.pieces if p and p.strip()]
    if not parts:
        return ""
    text = " ".join(parts)
    text = capitalize_sentence(text)
    if clause.closing and not text.endswith((".", "!", "?")):
        text += clause.closing
    return text


def _linker_starts_new_sentence(linker: str) -> bool:
    low = linker.strip().lower()
    if low in {",", ";", ":", "—", "-"}:
        return False
    return linker[:1].isupper() or low in {"но", "при", "например", "однако", "поэтому", "тогда"}


def attach_linker(prev: str, linker: str, nxt: str) -> str:
    link = linker.strip()
    if not link:
        return f"{prev} {nxt}"
    nxt_body = nxt[0].lower() + nxt[1:] if nxt else nxt
    if link in {",", ";", ":"}:
        return f"{prev.rstrip('.,!?')}{link} {nxt_body}"
    if link in {"—", "-"}:
        return f"{prev.rstrip('.,!?')} — {nxt_body}"
    if link.lower() == "и":
        return f"{prev.rstrip('.,!?')} и {nxt_body}"
    if _linker_starts_new_sentence(link) or prev.rstrip().endswith((".", "!", "?")):
        lead = link[:1].upper() + link[1:] if link else link
        return f"{prev} {lead} {nxt_body}"
    return f"{prev} {link} {nxt_body}"


def render_phrase(sketch: PhraseSketch) -> str:
    return render_clause(ClauseSketch(sketch.pieces, closing=sketch.closing))


def render_discourse(sketch: DiscourseSketch) -> str:
    paragraphs: list[str] = []
    bucket: list[str] = []
    for i, clause in enumerate(sketch.clauses):
        sent = render_clause(clause)
        if not sent:
            continue
        if clause.linker and bucket:
            bucket[-1] = attach_linker(bucket[-1], clause.linker, sent)
        else:
            bucket.append(sent)
        if i in sketch.paragraph_after:
            paragraphs.append(" ".join(bucket))
            bucket = []
    if bucket:
        paragraphs.append(" ".join(bucket))
    return "\n\n".join(paragraphs)


def clause_from_pieces(pieces: list[str], *, closing: str = ".", linker: str = "") -> ClauseSketch | None:
    clean = [p.strip() for p in pieces if p and p.strip()]
    if not clean:
        return None
    return ClauseSketch(clean, closing=closing, linker=linker)


def clause_from_slot_phrase(text: str, *, closing: str = ".", linker: str = "") -> ClauseSketch | None:
    phrase = re.sub(r"\s+", " ", str(text or "").strip())
    if not phrase:
        return None
    return ClauseSketch([phrase], closing=closing, linker=linker)


def paragraph_breaks(clause_scores: list[int]) -> set[int]:
    breaks: set[int] = set()
    for i in range(len(clause_scores) - 1):
        if clause_scores[i] - clause_scores[i + 1] >= 12:
            breaks.add(i)
    return breaks
