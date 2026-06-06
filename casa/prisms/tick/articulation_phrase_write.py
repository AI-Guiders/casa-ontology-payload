#!/usr/bin/env python3
"""Phrase-memory write path — compose answer from phrase events (no KB bundle)."""

from __future__ import annotations

import re
from typing import Any

from casa.prisms.visual.phrase_compose import load_phrase_events


def _tokens(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[\w\u0400-\u04FF]+", text, flags=re.UNICODE) if len(w) >= 3}


def _event_tokens(entry: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for w in entry.get("words") or []:
        if isinstance(w, dict) and w.get("surface"):
            out.add(str(w["surface"]).lower())
    for surface in entry.get("surfaces") or []:
        out |= _tokens(str(surface))
    return out


def pick_phrase_event(query: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
    qtok = _tokens(query)
    best: dict[str, Any] | None = None
    best_score = -1
    for entry in entries:
        score = len(qtok & _event_tokens(entry))
        if score > best_score:
            best_score = score
            best = entry
    return best or (entries[0] if entries else {})


def compose_phrase_write_answer(query: str, entry: dict[str, Any]) -> str:
    """Hot-path friendly answer from a matched phrase event."""
    surfaces = list(entry.get("surfaces") or [])
    phrase = surfaces[0] if surfaces else ""
    words = [str(w.get("surface") or "") for w in entry.get("words") or [] if isinstance(w, dict)]
    if not phrase and words:
        phrase = " ".join(words)
    agreement = entry.get("agreement") or []
    agr = ""
    if agreement and isinstance(agreement[0], dict):
        a = agreement[0]
        agr = (
            f" Согласование: {a.get('agent', '')} + {a.get('verb', '')}"
            f" ({a.get('kind', 'subjectVerb')})."
        )
    short_q = query.strip()
    if len(short_q) > 100:
        short_q = short_q[:97] + "…"
    event_id = str(entry.get("event_id") or "")
    body = f"На поле узнаю фразу «{phrase}»."
    if event_id:
        body += f" Event: {event_id}."
    body += agr
    return f"Понял: «{short_q}». {body}"


def phrase_write_from_query(
    query: str,
    *,
    events_path: str | None = None,
) -> dict[str, Any]:
    entries = load_phrase_events(events_path)
    entry = pick_phrase_event(query, entries)
    text = compose_phrase_write_answer(query, entry) if entry else ""
    return {
        "query": query,
        "answer_text": text,
        "event_id": entry.get("event_id") if entry else None,
        "matched": bool(entry),
    }
