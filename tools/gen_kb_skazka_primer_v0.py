#!/usr/bin/env python3
"""Primer story KB — text scenes + word cards (B2 vocabulary bootstrap)."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

DOC = "lab/kb/kb-skazka-primer-v1.md"

# Short primer tale: captions = «картинка» in text-only modality.
SCENES = [
    {"id": "s1", "caption": "Мама и папа.", "words": ["мама", "папа"]},
    {"id": "s2", "caption": "Кот сидит дома.", "words": ["кот", "дом"]},
    {"id": "s3", "caption": "Кот бежит в сад.", "words": ["кот", "сад"]},
    {"id": "s4", "caption": "Мама зовёт кота.", "words": ["мама", "кот"]},
    {"id": "s5", "caption": "Папа тоже зовёт.", "words": ["папа"]},
]

# New B2 words beyond bukvar primer (мама/папа may overlap — idempotent).
STORY_WORDS = ["мама", "папа", "кот", "дом", "сад"]

# Closed syllables for story words (B1 extension in skazka bundle).
EXTRA_SYLLABLES = ["кот", "дом", "сад"]

WORD_SYLLABLES: dict[str, list[str]] = {
    "мама": ["ма", "ма"],
    "папа": ["па", "па"],
    "кот": ["кот"],
    "дом": ["дом"],
    "сад": ["сад"],
}


def _compose_edges_for_syllable(syllable: str) -> list[dict]:
    dst = f"syllable.{syllable}"
    return [{"src": f"grapheme.{ch}", "relation": "compose", "dst": dst} for ch in syllable]


def _slug(text: str) -> str:
    t = re.sub(r"[^\w\s-]", "", text.lower(), flags=re.UNICODE)
    return re.sub(r"\s+", "_", t.strip())[:48]


def build_bundle() -> dict:
    claims: list[dict] = []
    edges: list[dict] = []

    for syl in EXTRA_SYLLABLES:
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

    for word, syls in WORD_SYLLABLES.items():
        claims.append(
            {
                "concept_id": f"lang.word.{word}",
                "claim_kind": "word",
                "text": f"слово {word}",
                "doc_path": DOC,
                "section": f"B2 / {word}",
                "slots": {"word": word, "syllables": syls},
            }
        )
        dst = f"lang.word.{word}"
        for syl in syls:
            edges.append({"src": f"syllable.{syl}", "relation": "compose", "dst": dst})

    for sc in SCENES:
        sid = sc["id"]
        cap = sc["caption"]
        claims.append(
            {
                "concept_id": f"ru.scene.{sid}",
                "claim_kind": "scene",
                "text": cap,
                "doc_path": DOC,
                "section": f"scene / {sid}",
                "slots": {"scene_id": sid, "caption": cap, "words": sc["words"]},
            }
        )
        for w in sc["words"]:
            edges.append({"src": f"ru.scene.{sid}", "relation": "shows", "dst": f"lang.word.{w}"})

    return {
        "schema_version": 1,
        "graph": {
            "root": {"id": DOC, "kind": "project_doc", "title": "kb-skazka-primer-v1"},
            "nodes": [{"id": DOC, "kind": "project_doc", "title": "kb-skazka-primer-v1"}],
            "edges": edges,
        },
        "claims": claims,
        "story": {"scenes": SCENES, "words": STORY_WORDS},
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("lab/kb/kb-skazka-primer-v1.payload.json"))
    p.add_argument("--session-out", type=Path, default=Path("lab/exp_sss_v1/skazka_read_session.json"))
    args = p.parse_args()
    bundle = build_bundle()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    session = {
        "title": "Читаем сказку: мама, кот, дом (text-only)",
        "modality": "text",
        "listen_copies": 3,
        "sleep": True,
        "scenes": SCENES,
    }
    args.session_out.parent.mkdir(parents=True, exist_ok=True)
    args.session_out.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "out": str(args.out.resolve()),
                "session": str(args.session_out.resolve()),
                "words": len(STORY_WORDS),
                "scenes": len(SCENES),
                "edges": len(bundle["graph"]["edges"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
