#!/usr/bin/env python3
"""Мета-грамматика literacy: лицо, падеж, согласование (ADR-0030)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_word_cards import merge_manifest, word_frame_id  # noqa: E402
from literacy_render import draw_text_centered  # noqa: E402
from meta_concepts import (  # noqa: E402
    GRAMMAR_AGREEMENT_PHRASE_CARDS,
    GRAMMAR_CASE_CARDS,
    GRAMMAR_GENDER_CARDS,
    GRAMMAR_NUMBER_CARDS,
    GRAMMAR_PERSON_CARDS,
    GRAMMAR_PERSON_PHRASE_CARDS,
    GRAMMAR_NUMERAL_CLASS_CARDS,
    GRAMMAR_NUMERAL_PHRASE_CARDS,
    GRAMMAR_POSSESSIVE_PHRASE_CARDS,
)

LESSON_PERSON = "lesson-08-grammar-meta"
LESSON_CASE = "lesson-08b-grammar-case-meta"
LESSON_AGREEMENT = "lesson-09-grammar-agreement-meta"
LESSON_POSSESSIVE = "lesson-09b-grammar-possessive-meta"
LESSON_NUMERAL = "lesson-09c-grammar-numeral-meta"
FACE = "sans"


def _font_size(surface: str) -> int:
    n = len(surface)
    if n <= 3:
        return 200
    if n <= 8:
        return 140
    if n <= 14:
        return 110
    return 90


def _build_cards(
    cards: list[tuple[str, str, str]],
    *,
    lesson_id: str,
    stage_id: str,
    stage_title: str,
    stage_order: int,
    grammar_tag: str,
) -> list[str]:
    img_dir = ROOT / lesson_id / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    frames: list[dict] = []
    for slug, surface, concept_id in cards:
        fid = word_frame_id(slug, face=FACE)
        draw_text_centered(surface, img_dir / f"{fid}.jpg", size=_font_size(surface))
        meta_tag = concept_id.removeprefix("lang.meta.")
        frames.append(
            {
                "id": fid,
                "path": f"{lesson_id}/images/{fid}.jpg",
                "scene_label": f"card:grammar:{meta_tag}:{FACE}",
                "concept_id": concept_id,
                "curriculum_tags": [
                    concept_id,
                    f"surface:{surface}",
                    f"slug:{slug}",
                    f"face:{FACE}",
                    f"grammar:{grammar_tag}",
                ],
                "lesson_id": lesson_id,
            }
        )
    merge_manifest(
        frames,
        stage_id=stage_id,
        stage_title=stage_title,
        stage_order=stage_order,
        lesson_id=lesson_id,
    )
    return [word_frame_id(slug, face=FACE) for slug, _, _ in cards]


def build_person_cards() -> list[str]:
    return _build_cards(
        [*GRAMMAR_PERSON_CARDS, *GRAMMAR_PERSON_PHRASE_CARDS],
        lesson_id=LESSON_PERSON,
        stage_id="stage-08-meta-grammar-person",
        stage_title="Мета-грамматика: грамматическое лицо",
        stage_order=80,
        grammar_tag="person",
    )


def build_case_cards() -> list[str]:
    return _build_cards(
        GRAMMAR_CASE_CARDS,
        lesson_id=LESSON_CASE,
        stage_id="stage-08b-meta-grammar-case",
        stage_title="Мета-грамматика: падеж (им / вин)",
        stage_order=81,
        grammar_tag="case",
    )


def build_agreement_cards() -> list[str]:
    return _build_cards(
        GRAMMAR_AGREEMENT_PHRASE_CARDS,
        lesson_id=LESSON_AGREEMENT,
        stage_id="stage-09-grammar-agreement-pilot",
        stage_title="Согласование: пары форм",
        stage_order=82,
        grammar_tag="agreement",
    )


def build_numeral_cards() -> list[str]:
    return _build_cards(
        [*GRAMMAR_NUMERAL_CLASS_CARDS, *GRAMMAR_NUMERAL_PHRASE_CARDS],
        lesson_id=LESSON_NUMERAL,
        stage_id="stage-09c-grammar-numeral",
        stage_title="Числительное + существительное (классы 1 / 2–4 / 5+)",
        stage_order=84,
        grammar_tag="numeral",
    )


def build_possessive_cards() -> list[str]:
    return _build_cards(
        [*GRAMMAR_POSSESSIVE_PHRASE_CARDS, *GRAMMAR_GENDER_CARDS, *GRAMMAR_NUMBER_CARDS],
        lesson_id=LESSON_POSSESSIVE,
        stage_id="stage-09b-grammar-possessive",
        stage_title="Род/число: притяжательное (мой/моя/моё)",
        stage_order=83,
        grammar_tag="possessive",
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--person", action="store_true")
    p.add_argument("--case", action="store_true")
    p.add_argument("--agreement", action="store_true")
    p.add_argument("--possessive", action="store_true")
    p.add_argument("--numeral", action="store_true")
    p.add_argument("--all", action="store_true", help="person + case + agreement + possessive + numeral")
    args = p.parse_args()
    if args.all or not (args.person or args.case or args.agreement or args.possessive or args.numeral):
        args.person = args.case = args.agreement = args.possessive = args.numeral = True
    out: dict[str, list[str]] = {}
    if args.person:
        out["person"] = build_person_cards()
    if args.case:
        out["case"] = build_case_cards()
    if args.agreement:
        out["agreement"] = build_agreement_cards()
    if args.possessive:
        out["possessive"] = build_possessive_cards()
    if args.numeral:
        out["numeral"] = build_numeral_cards()
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
