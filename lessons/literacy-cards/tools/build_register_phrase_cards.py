#!/usr/bin/env python3
"""Категория регистра: два русских имени → один semantic concept_id (не транслит slug)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_word_cards import merge_manifest, word_frame_id  # noqa: E402
from literacy_render import draw_text_centered  # noqa: E402
from meta_concepts import LETTER_CASE_LOWER, LETTER_CASE_UPPER  # noqa: E402

LESSON_ID = "lesson-07-meta-language"
STAGE_ID = "stage-07c-register-phrases"
STAGE_ORDER = 72
FACE = "sans"

# (slug, surface, concept_id) — один concept, два frame на категорию
FRAMES = [
    ("capital-zaglavnaya-bukva", "заглавная буква", LETTER_CASE_UPPER),
    ("capital-verhnego-registra", "буква верхнего регистра", LETTER_CASE_UPPER),
    ("lowercase-strochnaya-bukva", "строчная буква", LETTER_CASE_LOWER),
    ("lowercase-nizhnego-registra", "буква нижнего регистра", LETTER_CASE_LOWER),
]


def main() -> None:
    img_dir = ROOT / LESSON_ID / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    manifest_frames: list[dict] = []
    for slug, surface, cid in FRAMES:
        fid = word_frame_id(slug, face=FACE)
        size = 88 if len(surface) > 14 else 110
        draw_text_centered(surface, img_dir / f"{fid}.jpg", size=size)
        manifest_frames.append(
            {
                "id": fid,
                "path": f"{LESSON_ID}/images/{fid}.jpg",
                "scene_label": f"card:register:{cid.rsplit('.', 1)[-1]}:{FACE}",
                "concept_id": cid,
                "curriculum_tags": [cid, f"surface:{surface}", f"slug:{slug}", f"face:{FACE}"],
                "lesson_id": LESSON_ID,
            }
        )
    merge_manifest(
        manifest_frames,
        stage_id=STAGE_ID,
        stage_title="Категория: буква регистра (фразы)",
        stage_order=STAGE_ORDER,
        lesson_id=LESSON_ID,
    )
    print(
        json.dumps(
            {"stage": STAGE_ID, "concepts": [LETTER_CASE_UPPER, LETTER_CASE_LOWER]},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
