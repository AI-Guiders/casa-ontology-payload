#!/usr/bin/env python3
"""Corpus word index — surface ↔ slug from lesson manifest (W1 R1)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from casa.prisms.memory.meta_concept_aliases import canonical_lex_concept_id
from casa.prisms.visual.syllabify_ru import normalize_surface, syllabify_ru, syllable_concept_ids

_MANIFEST = (
    Path(__file__).resolve().parents[3] / "lessons" / "literacy-cards" / "class.manifest.json"
)


@lru_cache(maxsize=1)
def _corpus_by_slug() -> dict[str, dict[str, Any]]:
    if not _MANIFEST.is_file():
        return {}
    doc = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    out: dict[str, dict[str, Any]] = {}
    for fr in doc.get("frames") or []:
        if not isinstance(fr, dict):
            continue
        cid = str(fr.get("concept_id") or "")
        if not cid.startswith("lang.word."):
            continue
        slug = cid.removeprefix("lang.word.")
        surface = ""
        for tag in fr.get("curriculum_tags") or []:
            ts = str(tag)
            if ts.startswith("word:"):
                surface = ts[5:]
                break
        if not surface:
            continue
        out[slug] = {
            "slug": slug,
            "surface": surface,
            "word_concept_id": canonical_lex_concept_id(cid),
            "corpus_frame_id": str(fr.get("id") or f"word-{slug}-sans"),
            "lesson_id": str(fr.get("lesson_id") or ""),
        }
    return out


@lru_cache(maxsize=1)
def _corpus_by_surface() -> dict[str, dict[str, Any]]:
    return {normalize_surface(r["surface"]): dict(r) for r in _corpus_by_slug().values()}


def lookup_corpus_word(*, slug: str = "", surface: str = "") -> dict[str, Any] | None:
    key = str(slug or "").strip()
    if key:
        row = _corpus_by_slug().get(key)
        return dict(row) if row else None
    surf = normalize_surface(surface)
    if surf:
        row = _corpus_by_surface().get(surf)
        return dict(row) if row else None
    return None


def analytic_entry_from_corpus(*, slug: str = "", surface: str = "") -> dict[str, Any] | None:
    """Build R1 entry: syllabify(surface) + corpus slug — no sidecar JSON."""
    row = lookup_corpus_word(slug=slug, surface=surface)
    if not row:
        return None
    surf = str(row["surface"])
    syllables = syllabify_ru(surf)
    return {
        "surface": surf,
        "slug": str(row["slug"]),
        "syllables": syllables,
        "syllable_concept_ids": syllable_concept_ids(syllables),
        "corpus_frame_id": row.get("corpus_frame_id"),
        "source": "corpus_lexicon",
    }
