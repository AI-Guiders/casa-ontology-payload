#!/usr/bin/env python3
"""Generate kb-bukvar-ru-full-v1.payload.json — full Cyrillic B0 + complete open B1."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import argparse
import json
from pathlib import Path

DOC = "lab/kb/kb-bukvar-ru-full-v1.md"

# Full alphabet (B0)
RU_ALPHABET = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"

# Open-syllable inventory (B1): V + CV — finite complete set for Russian bukvar.
RU_VOWELS = "аеёиоуыэюя"
RU_CONSONANTS = "бвгджзйклмнпрстфхцчшщ"

# Closed / special syllables for ъ, ь and primer words (мама, папа).
SPECIAL_SYLLABLES = [
    "мам",
    "пап",
    "объ",
    "съ",
    "изъ",
    "ль",
    "нь",
    "сь",
    "ть",
    "дь",
    "мь",
    "пь",
]

PRIMER_WORDS = ["мама", "папа"]


def all_open_syllables() -> list[str]:
    """V (10) + CV (21×10) = 220 open syllables."""
    out: list[str] = []
    seen: set[str] = set()
    for v in RU_VOWELS:
        if v not in seen:
            out.append(v)
            seen.add(v)
    for c in RU_CONSONANTS:
        for v in RU_VOWELS:
            syl = c + v
            if syl not in seen:
                out.append(syl)
                seen.add(syl)
    return out


def all_syllables_v1() -> list[str]:
    """Open syllables + special (ъ/ь coverage, primer CVC)."""
    seen: set[str] = set()
    ordered: list[str] = []
    for syl in all_open_syllables() + SPECIAL_SYLLABLES:
        if syl not in seen:
            ordered.append(syl)
            seen.add(syl)
    return ordered


def grapheme_coverage(syllables: list[str]) -> tuple[set[str], set[str]]:
    covered: set[str] = set()
    for syl in syllables:
        covered.update(syl)
    missing = set(RU_ALPHABET) - covered
    return covered, missing


def _compose_edges_for_syllable(syllable: str) -> list[dict]:
    edges: list[dict] = []
    dst = f"syllable.{syllable}"
    for ch in syllable:
        edges.append({"src": f"grapheme.{ch}", "relation": "compose", "dst": dst})
    return edges


def _word_syllable_parts(word: str, syllables: list[str]) -> list[str]:
    """Greedy longest-match syllable segmentation for primer words."""
    syl_set = set(syllables)
    parts: list[str] = []
    i = 0
    while i < len(word):
        matched = False
        for ln in range(min(4, len(word) - i), 0, -1):
            chunk = word[i : i + ln]
            if chunk in syl_set:
                parts.append(chunk)
                i += ln
                matched = True
                break
        if not matched:
            parts.append(word[i])
            i += 1
    return parts


def _compose_edges_for_word(word: str, syllables: list[str]) -> list[dict]:
    edges: list[dict] = []
    dst = f"lang.word.{word}"
    for syl in _word_syllable_parts(word, syllables):
        if f"syllable.{syl}" in {f"syllable.{s}" for s in syllables}:
            edges.append({"src": f"syllable.{syl}", "relation": "compose", "dst": dst})
    return edges


def build_bundle() -> dict:
    claims: list[dict] = []
    edges: list[dict] = []

    for letter in RU_ALPHABET:
        claims.append(
            {
                "concept_id": f"grapheme.{letter}",
                "claim_kind": "grapheme",
                "text": f"буква {letter}",
                "doc_path": DOC,
                "section": f"B0 / {letter}",
                "slots": {"letter": letter},
            }
        )

    syllables = all_syllables_v1()
    for syl in syllables:
        claims.append(
            {
                "concept_id": f"syllable.{syl}",
                "claim_kind": "syllable",
                "text": f"слог {syl}",
                "doc_path": DOC,
                "section": f"B1 / {syl}",
                "slots": {"syllable": syl},
            }
        )
        edges.extend(_compose_edges_for_syllable(syl))

    for word in PRIMER_WORDS:
        claims.append(
            {
                "concept_id": f"lang.word.{word}",
                "claim_kind": "word",
                "text": f"слово {word}",
                "doc_path": DOC,
                "section": f"B2 / {word}",
                "slots": {"word": word},
            }
        )
        edges.extend(_compose_edges_for_word(word, syllables))

    return {
        "schema_version": 1,
        "graph": {
            "root": {"id": DOC, "kind": "project_doc", "title": "kb-bukvar-ru-full-v1"},
            "nodes": [{"id": DOC, "kind": "project_doc", "title": "kb-bukvar-ru-full-v1"}],
            "edges": edges,
        },
        "claims": claims,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--out",
        type=Path,
        default=Path("lab/kb/kb-bukvar-ru-full-v1.payload.json"),
    )
    args = p.parse_args()
    bundle = build_bundle()
    syllables = all_syllables_v1()
    covered, missing = grapheme_coverage(syllables)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    g = sum(1 for c in bundle["claims"] if c["concept_id"].startswith("grapheme."))
    s = sum(1 for c in bundle["claims"] if c["concept_id"].startswith("syllable."))
    w = sum(1 for c in bundle["claims"] if c["concept_id"].startswith("lang.word."))
    open_n = len(all_open_syllables())
    print(
        json.dumps(
            {
                "out": str(args.out.resolve()),
                "graphemes": g,
                "syllables": s,
                "syllables_open": open_n,
                "syllables_special": s - open_n,
                "words": w,
                "compose_edges": len(bundle["graph"]["edges"]),
                "grapheme_coverage": len(covered),
                "grapheme_missing": sorted(missing),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
