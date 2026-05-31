#!/usr/bin/env python3
"""Grapheme concept helpers for VK compose decode."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

from casa.prisms.memory.grapheme_ingest import GRAPHEME_CYRL_PREFIX, GRAPHEME_LATN_PREFIX


def is_cyrillic(ch: str) -> bool:
    return len(ch) == 1 and "\u0400" <= ch <= "\u04ff"


def grapheme_concept_for_char(ch: str) -> tuple[str, str]:
    """Return (concept_id, script) for one output character."""
    if not ch:
        raise ValueError("empty char")
    if is_cyrillic(ch):
        return f"{GRAPHEME_CYRL_PREFIX}{ch.lower()}", "cyrl"
    return f"{GRAPHEME_LATN_PREFIX}{ch.lower()}", "latn"


def char_from_grapheme_concept(concept_id: str) -> str | None:
    cid = concept_id or ""
    if cid.startswith(GRAPHEME_LATN_PREFIX):
        return cid[len(GRAPHEME_LATN_PREFIX) :][:1] or None
    if cid.startswith(GRAPHEME_CYRL_PREFIX):
        return cid[len(GRAPHEME_CYRL_PREFIX) :][:1] or None
    return None
