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


# name-edge set + reverse index (surface → concepts), memoised per lattice content — the
# parser resolves EVERY token through concepts_for_term, which must be a dict hit, not a
# scan of all name edges. Same invalidation signature as concept_net.decoded_edges.
_NAME_CACHE: dict[int, tuple[tuple[int, int], set[str], dict[str, list[str]]]] = {}


def _name_tables(state: dict, lattice_id: str) -> tuple[set[str], dict[str, list[str]]]:
    from casa.curriculum.concept_net import decoded_edges
    from casa.prisms.memory.memory_prisms import memory_lattices

    lat = memory_lattices(state).get(lattice_id)
    if not lat:
        return set(), {}
    cells = lat.get("cells") or []
    sig = (id(cells), sum(len(c) for c in cells))
    hit = _NAME_CACHE.get(id(lat))
    if hit is not None and hit[0] == sig:
        return hit[1], hit[2]
    edges = {e for e in decoded_edges(lat) if _NAMES in e}
    index: dict[str, list[str]] = {}
    for e in edges:
        concept, _, surface = e.partition(_NAMES)
        index.setdefault(surface, []).append(concept)
    _NAME_CACHE[id(lat)] = (sig, edges, index)
    return edges, index


def _name_edges(state: dict, lattice_id: str) -> set[str]:
    return _name_tables(state, lattice_id)[0]


def concepts_for_term(state: dict, lattice_id: str, word: str, lang: str | None = None) -> list[str]:
    """Concepts that name ``word`` (reverse names lookup). A tagged ``lang`` («es») looks up
    ONLY that language's tagged names; the default sees only untagged (RU/EN) ones."""
    key = f"{lang}.{word}" if lang in _TAGGED_LANGS else str(word)
    return sorted(set(_name_tables(state, lattice_id)[1].get(key, [])))


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
