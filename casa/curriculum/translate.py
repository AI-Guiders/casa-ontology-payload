#!/usr/bin/env python3
"""Concept-mediated term translation (RU <-> EN) over the field's name edges.

The field records ``concept|names|lang.word.<surface>`` edges in either script when
a concept is taught its word(s). Translation of a TERM is then a two-hop graph walk
on those edges, with NO statistical model:

    одиннадцать --(reverse names)--> math.num.eleven --(names, latn)--> eleven

This is deterministic, auditable, and hallucination-free — strong for controlled
vocabulary / domain glossaries (e.g. medical terminology), and bounded to terms the
field actually knows (it returns nothing rather than inventing). Sentence-level
translation needs a language-agnostic meaning layer (a separate, larger task);
this covers words/terms, which is what the substrate supports today.
"""

from __future__ import annotations

_NAMES = "|names|lang.word."
# Languages that share the Latin script with English carry an explicit tag INSIDE the
# name edge (``concept.file|names|lang.word.es.archivo``) — script detection cannot tell
# them from English, so tagged surfaces are invisible to every script-routed path
# (realization, RU<->EN term translation) and visible only to lang-aware lookups.
_TAGGED_LANGS = ("es",)


def _lang_tag_of(surface: str) -> str | None:
    """The language tag of a tagged name surface ('es.archivo' → 'es'), else None."""
    for tag in _TAGGED_LANGS:
        if surface.startswith(tag + "."):
            return tag
    return None


def script_of(surface: str) -> str:
    """'cyrl' if the surface contains any Cyrillic letter, else 'latn'."""
    return "cyrl" if any("Ѐ" <= ch <= "ӿ" for ch in str(surface)) else "latn"


def _name_edges(state: dict, lattice_id: str) -> set[str]:
    from casa.prisms.memory.f0_stack import decode_f0_lattice
    from casa.prisms.memory.memory_prisms import memory_lattices

    lat = memory_lattices(state).get(lattice_id)
    if not lat:
        return set()
    return {e for e in (decode_f0_lattice(lat).get("edges") or []) if _NAMES in e}


def concepts_for_term(state: dict, lattice_id: str, word: str, lang: str | None = None) -> list[str]:
    """Concepts that name ``word`` (reverse names lookup). A tagged ``lang`` («es») looks up
    ONLY that language's tagged names; the default sees only untagged (RU/EN) ones."""
    suffix = f"{_NAMES}{lang}.{word}" if lang in _TAGGED_LANGS else f"{_NAMES}{word}"
    return sorted({e.split("|names|")[0] for e in _name_edges(state, lattice_id) if e.endswith(suffix)})


def translate_term(state: dict, lattice_id: str, word: str, *, to_script: str) -> list[str]:
    """Translate ``word`` to ``to_script`` ('latn'/'cyrl') via the shared concept(s).

    Returns the target-script surfaces named by any concept that names ``word``
    (deduplicated, sorted). Empty if the field knows no such mapping.
    """
    concepts = set(concepts_for_term(state, lattice_id, word))
    if not concepts:
        return []
    out: set[str] = set()
    for edge in _name_edges(state, lattice_id):
        concept, _, surface = edge.partition(_NAMES)
        if _lang_tag_of(surface):  # tagged languages never surface in RU<->EN translation
            continue
        if concept in concepts and surface != word and script_of(surface) == to_script:
            out.add(surface)
    return sorted(out)
