#!/usr/bin/env python3
"""Один кейс: слово апельсин / Апельсин (регистр на уровне целого слова)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_word_cards import build_frames, merge_manifest, word_frame_id  # noqa: E402
from literacy_render import draw_text_centered  # noqa: E402

LESSON_ID = "lesson-03-words-cyrl"
STAGE_ID = "stage-03b-words-case-apelsin"
PAIRS = [
    ("apelsin", "апельсин"),
    ("apelsin_cap", "Апельсин"),
]


def main() -> None:
    img_dir = ROOT / LESSON_ID / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    for slug, surface in PAIRS:
        draw_text_centered(surface, img_dir / f"{word_frame_id(slug)}.jpg", size=120)
    frames = build_frames(PAIRS, lesson_id=LESSON_ID)
    merge_manifest(
        frames,
        stage_id=STAGE_ID,
        stage_title="Слова: регистр (апельсин)",
        stage_order=35,
        lesson_id=LESSON_ID,
    )
    print(json.dumps({"frames": [f["id"] for f in frames]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
