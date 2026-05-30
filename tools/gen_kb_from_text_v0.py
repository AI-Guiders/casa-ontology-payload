#!/usr/bin/env python3
"""Build dynamic word bundle from extracted text — compose from syllable signal."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sss_segment_candidates_v0 import segment_vowel_nuclei_from_signal  # type: ignore
from sss_text_tokenize_v0 import extract_punctuation_unique, extract_words, norm_text  # type: ignore
from sss_vocab_v0 import punct_concept_id  # type: ignore


def syllables_from_bukvar(bundle: dict) -> set[str]:
    out: set[str] = set()
    for c in bundle.get("claims") or []:
        cid = str(c.get("concept_id") or "")
        if cid.startswith("syllable."):
            out.add(cid[len("syllable.") :])
    return out


def segment_word_to_syllables(word: str, known: set[str]) -> list[str]:
    """Greedy longest-match on known syllables, else vowel-nuclei chunks from signal."""
    w = word.lower()
    parts: list[str] = []
    i = 0
    while i < len(w):
        match = None
        for ln in range(min(6, len(w) - i), 0, -1):
            chunk = w[i : i + ln]
            if chunk in known:
                match = chunk
                break
        if match:
            parts.append(match)
            i += len(match)
        else:
            break
    if parts and "".join(parts) == w:
        return parts
    nuclei = segment_vowel_nuclei_from_signal(w)
    return nuclei if nuclei and "".join(nuclei) == w else [w]


def _compose_edges_for_syllable(syllable: str) -> list[dict]:
    dst = f"syllable.{syllable}"
    return [{"src": f"grapheme.{ch}", "relation": "compose", "dst": dst} for ch in syllable]


def build_bundle_from_text(
    text: str,
    *,
    bukvar_bundle: dict | None = None,
    doc_path: str = "lab/text/ingested.txt",
    title: str = "text-ingest-dynamic",
) -> dict[str, Any]:
    """Dynamic KB slice: words found in text + syllables needed for compose."""
    known = syllables_from_bukvar(bukvar_bundle or {"claims": []})
    words = extract_words(text, min_len=1)
    claims: list[dict] = []
    edges: list[dict] = []
    extra_syl: set[str] = set()

    word_syllables: dict[str, list[str]] = {}
    for w in words:
        syls = segment_word_to_syllables(w, known)
        word_syllables[w] = syls
        for s in syls:
            if s not in known:
                extra_syl.add(s)

    for syl in sorted(extra_syl):
        claims.append(
            {
                "concept_id": f"syllable.{syl}",
                "claim_kind": "syllable",
                "text": f"слог {syl}",
                "doc_path": doc_path,
                "slots": {"syllable": syl, "source": "text_extract"},
            }
        )
        edges.extend(_compose_edges_for_syllable(syl))
        known.add(syl)

    for w in words:
        syls = word_syllables[w]
        claims.append(
            {
                "concept_id": f"lang.word.{w}",
                "claim_kind": "word",
                "text": f"слово {w}",
                "doc_path": doc_path,
                "slots": {"word": w, "syllables": syls, "source": "text_extract"},
            }
        )
        dst = f"lang.word.{w}"
        for s in syls:
            edges.append({"src": f"syllable.{s}", "relation": "compose", "dst": dst})

    marks = extract_punctuation_unique(text)
    for mark in marks:
        cid = punct_concept_id(mark)
        claims.append(
            {
                "concept_id": cid,
                "claim_kind": "punctuation",
                "text": f"знак {mark}",
                "doc_path": doc_path,
                "slots": {"mark": mark, "source": "text_extract"},
            }
        )
        if len(mark) == 1:
            claims.append(
                {
                    "concept_id": f"grapheme.{mark}",
                    "claim_kind": "grapheme",
                    "text": f"буква/знак {mark}",
                    "doc_path": doc_path,
                    "slots": {"letter": mark, "source": "punctuation"},
                }
            )

    return {
        "schema_version": 1,
        "graph": {
            "root": {"id": doc_path, "kind": "text_ingest", "title": title},
            "nodes": [{"id": doc_path, "kind": "text_ingest", "title": title}],
            "edges": edges,
        },
        "claims": claims,
        "extract": {
            "words": words,
            "word_syllables": word_syllables,
            "extra_syllables": sorted(extra_syl),
            "punctuation": marks,
        },
    }


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Build dynamic word bundle from plain text")
    p.add_argument("--text", type=Path, required=True)
    p.add_argument("--bukvar", type=Path, default=Path("lab/kb/kb-bukvar-ru-full-v1.payload.json"))
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--title", default="text-ingest-dynamic")
    args = p.parse_args()

    text = norm_text(args.text.read_text(encoding="utf-8"))
    bukvar = json.loads(args.bukvar.read_text(encoding="utf-8")) if args.bukvar.exists() else None
    bundle = build_bundle_from_text(text, bukvar_bundle=bukvar, doc_path=str(args.text), title=args.title)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    ex = bundle.get("extract") or {}
    print(
        json.dumps(
            {
                "out": str(args.out.resolve()),
                "words": len(ex.get("words") or []),
                "punctuation": len(ex.get("punctuation") or []),
                "extra_syllables": len(ex.get("extra_syllables") or []),
                "edges": len(bundle["graph"]["edges"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
