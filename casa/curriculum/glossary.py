#!/usr/bin/env python3
"""Bulk bilingual glossary — teach many RU<->EN word pairs in a SINGLE sleep.

teach() runs one sleep per concept, which does not scale to thousands of words.
teach_glossary appends every pair's episode first, then runs ONE consolidation
sleep that mints all the concept|names|word edges at once — so a large open
bilingual list (Wiktionary / FreeDict / a frequency list; NOT the proprietary
Oxford dictionary) can be loaded as a deterministic, hallucination-free glossary.

This is term-level translation memory — memorized word pairs, not fluent
translation or sentence understanding (which needs a language-agnostic meaning
layer). The lattice must have cell capacity for the vocabulary size; very large
lists want a dedicated lexicon lattice rather than schema-math.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


def _concept_id(en: str, prefix: str) -> str:
    return f"{prefix}{en.strip().lower().replace(' ', '_')}"


def teach_glossary(
    state: dict,
    pairs: Iterable[tuple[str, str]],
    *,
    lattice_id: str = "schema-math",
    bundle: dict[str, Any] | None = None,
    concept_prefix: str = "concept.",  # ADR-0085: concept.* hub (was lex.*)
) -> dict[str, Any]:
    """Teach ``(ru, en)`` pairs in one sleep. Returns ``{taught, concepts}``."""
    from casa.prisms.memory.memory_prisms import append_episode, run_sleep

    bundle = bundle or {"claims": [], "graph": {"edges": []}}
    concepts: list[str] = []
    for ru, en in pairs:
        ru, en = str(ru).strip(), str(en).strip()
        if not ru or not en:
            continue
        cid = _concept_id(en, concept_prefix)
        append_episode(
            state,
            cue=en,
            surface_attempt="?",
            correct=en,
            lattice_id=lattice_id,
            concept_id=cid,
            scene=f"ru: {ru} | en: {en}",
            structure_tag="self_promote",  # sanctioned earned-write
        )
        concepts.append(cid)
    # ONE consolidation sleep mints every bilingual names edge in the batch
    run_sleep(state, bundle)
    return {"taught": len(concepts), "concepts": concepts}


def load_pairs(path: str | Path) -> list[tuple[str, str]]:
    """Load (ru, en) pairs from JSON (``[["ru","en"], ...]`` or ``[{"ru","en"}, ...]``)
    or a TSV file (``ru<TAB>en`` per line). Lets an open dictionary be plugged in."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        data = json.loads(text)
        out: list[tuple[str, str]] = []
        for row in data:
            if isinstance(row, dict):
                out.append((str(row.get("ru") or ""), str(row.get("en") or "")))
            elif isinstance(row, (list, tuple)) and len(row) >= 2:
                out.append((str(row[0]), str(row[1])))
        return out
    pairs: list[tuple[str, str]] = []
    for line in text.splitlines():
        if "\t" in line:
            ru, en = line.split("\t", 1)
            pairs.append((ru.strip(), en.strip()))
    return pairs
