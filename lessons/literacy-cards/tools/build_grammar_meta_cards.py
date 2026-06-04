#!/usr/bin/env python3
"""Мета-грамматика literacy: лицо (ADR-0030) → lesson-08-grammar-meta."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_word_cards import merge_manifest, word_frame_id  # noqa: E402
from literacy_render import draw_text_centered  # noqa: E402
from meta_concepts import GRAMMAR_PERSON_CARDS  # noqa: E402

LESSON_ID = "lesson-08-grammar-meta"
FACE = "sans"
STAGE_PERSON = (
    "stage-08-meta-grammar-person",
    "Мета-грамматика: грамматическое лицо",
    80,
)


def _font_size(surface: str) -> int:
    n = len(surface)
    if n <= 3:
        return 200
    if n <= 8:
        return 140
    return 110


def build_person_cards() -> list[str]:
    stage_id, stage_title, stage_order = STAGE_PERSON
    img_dir = ROOT / LESSON_ID / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    frames: list[dict] = []
    for slug, surface, concept_id in GRAMMAR_PERSON_CARDS:
        fid = word_frame_id(slug, face=FACE)
        draw_text_centered(surface, img_dir / f"{fid}.jpg", size=_font_size(surface))
        meta_tag = concept_id.removeprefix("lang.meta.")
        frames.append(
            {
                "id": fid,
                "path": f"{LESSON_ID}/images/{fid}.jpg",
                "scene_label": f"card:grammar:{meta_tag}:{FACE}",
                "concept_id": concept_id,
                "curriculum_tags": [
                    concept_id,
                    f"surface:{surface}",
                    f"slug:{slug}",
                    f"face:{FACE}",
                    "grammar:person",
                ],
                "lesson_id": LESSON_ID,
            }
        )
    merge_manifest(
        frames,
        stage_id=stage_id,
        stage_title=stage_title,
        stage_order=stage_order,
        lesson_id=LESSON_ID,
    )
    return [word_frame_id(s, face=FACE) for s, _, _ in GRAMMAR_PERSON_CARDS]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--person", action="store_true", help="build stage-08 person cards (default)")
    args = p.parse_args()
    _ = args
    ids = build_person_cards()
    print(
        json.dumps(
            {"lesson": LESSON_ID, "stage": STAGE_PERSON[0], "frames": ids},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
