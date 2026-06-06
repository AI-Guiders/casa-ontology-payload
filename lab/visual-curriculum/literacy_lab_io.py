"""Lab I/O — corpus slugs for analytic breakdown / probes (no sidecar JSON)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
_DEFAULT_PHRASE_EVENTS = (
    _REPO / "lessons" / "literacy-cards" / "data" / "literacy" / "phrase-events-ru-pilot-v1.json"
)


def _words_from_phrase_event(ev: dict[str, Any]) -> list[dict[str, Any]]:
    words: list[dict[str, Any]] = []
    for block in ev.get("words") or []:
        if isinstance(block, dict):
            words.append(block)
    for ex in ev.get("examples") or []:
        if not isinstance(ex, dict):
            continue
        for block in ex.get("words") or []:
            if isinstance(block, dict):
                words.append(block)
    return words


def slugs_from_phrase_events(path: Path | str | None = None) -> list[str]:
    from casa.prisms.visual.phrase_compose import load_phrase_events

    p = Path(path) if path else _DEFAULT_PHRASE_EVENTS
    slugs: list[str] = []
    seen: set[str] = set()
    for ev in load_phrase_events(p):
        for word in _words_from_phrase_event(ev):
            slug = str(word.get("slug") or "").strip()
            if slug and slug not in seen:
                slugs.append(slug)
                seen.add(slug)
    return slugs


def analytic_entries_for_slugs(slugs: list[str]) -> list[dict[str, Any]]:
    from casa.prisms.visual.corpus_lexicon import analytic_entry_from_corpus

    out: list[dict[str, Any]] = []
    for slug in slugs:
        key = str(slug or "").strip()
        if not key:
            continue
        ent = analytic_entry_from_corpus(slug=key)
        if ent:
            out.append(ent)
    return out
