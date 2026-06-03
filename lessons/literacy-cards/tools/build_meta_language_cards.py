#!/usr/bin/env python3
"""Метаязык literacy (text tract): волны 1–2, episodic на lexicon-ru."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_word_cards import merge_manifest, word_frame_id  # noqa: E402
from literacy_render import draw_text_centered  # noqa: E402
from meta_concepts import WAVE2_CARDS  # noqa: E402

LESSON_ID = "lesson-07-meta-language"
FACE = "sans"

WAVE1 = [
    ("bukva", "буква"),
    ("slovo", "слово"),
    ("zaglavnaya", "заглавная"),
    ("strochnaya", "строчная"),
]

STAGES = {
    1: ("stage-07-meta-language", "Метаязык: буква, слово, регистр", 7),
    2: ("stage-07b-meta-language-2", "Метаязык: эпистемика, грамматика", 71),
}


def _font_size(surface: str) -> int:
    n = len(surface)
    if n <= 8:
        return 140
    if n <= 12:
        return 110
    return 88


def _build_word_pairs(pairs: list[tuple[str, str]], stage_id: str, stage_title: str, stage_order: int) -> list[str]:
    from build_word_cards import build_frames  # noqa: E402

    img_dir = ROOT / LESSON_ID / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    for slug, surface in pairs:
        draw_text_centered(surface, img_dir / f"{word_frame_id(slug)}.jpg", size=_font_size(surface))
    frames = build_frames(pairs, lesson_id=LESSON_ID)
    merge_manifest(frames, stage_id=stage_id, stage_title=stage_title, stage_order=stage_order, lesson_id=LESSON_ID)
    return [word_frame_id(s) for s, _ in pairs]


def _build_meta_cards(cards: list[tuple[str, str, str]], stage_id: str, stage_title: str, stage_order: int) -> list[str]:
    img_dir = ROOT / LESSON_ID / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    frames: list[dict] = []
    for slug, surface, concept_id in cards:
        fid = word_frame_id(slug, face=FACE)
        draw_text_centered(surface, img_dir / f"{fid}.jpg", size=_font_size(surface))
        meta_tag = concept_id.removeprefix("lang.meta.").removeprefix("lang.word.")
        frames.append(
            {
                "id": fid,
                "path": f"{LESSON_ID}/images/{fid}.jpg",
                "scene_label": f"card:meta:{meta_tag}:{FACE}",
                "concept_id": concept_id,
                "curriculum_tags": [concept_id, f"surface:{surface}", f"slug:{slug}", f"face:{FACE}"],
                "lesson_id": LESSON_ID,
            }
        )
    merge_manifest(frames, stage_id=stage_id, stage_title=stage_title, stage_order=stage_order, lesson_id=LESSON_ID)
    return [word_frame_id(s, face=FACE) for s, _, _ in cards]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--wave", type=int, choices=(1, 2), default=1)
    args = p.parse_args()
    sid, title, order = STAGES[args.wave]
    if args.wave == 1:
        ids = _build_word_pairs(WAVE1, sid, title, order)
    else:
        ids = _build_meta_cards(WAVE2_CARDS, sid, title, order)
    print(json.dumps({"wave": args.wave, "stage": sid, "frames": ids}, ensure_ascii=False))


if __name__ == "__main__":
    main()
