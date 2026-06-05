#!/usr/bin/env python3
"""Мета-фонология: гласная / согласная (ADR-0030 L2) + буквы с подписью категории."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_letter_cards import CYRILLIC  # noqa: E402
from build_word_cards import merge_manifest  # noqa: E402
from literacy_render import draw_letter_with_label, draw_text_centered  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LESSON_ID = "lesson-09-phonology-meta"
STAGE_ID = "stage-04-meta-phonology-vowel-consonant"
STAGE_TITLE = "Мета-фонология: гласная и согласная"
STAGE_ORDER = 4
FACE = "sans"

META_VOWEL = "lang.meta.phonology.vowel"
META_CONSONANT = "lang.meta.phonology.consonant"
LABEL_VOWEL = "гласная"
LABEL_CONSONANT = "согласная"

VOWEL_LIST = ROOT / "data" / "ru-cyrl-vowel-cues-v1.txt"


def _load_vowel_cues(path: Path) -> set[str]:
    cues: set[str] = set()
    for ln in path.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        cues.add(s)
    return cues


def _cyrl_by_cue() -> dict[str, tuple[str, str, str]]:
    return {c: (c, lo, up) for c, lo, up in CYRILLIC}


def _category_frame(*, fid: str, surface: str, concept_id: str, slug: str) -> dict:
    facet = "vowel" if concept_id.endswith(".vowel") else "consonant"
    return {
        "id": fid,
        "path": f"{LESSON_ID}/images/{fid}.jpg",
        "scene_label": f"card:phonology:meta:{facet}:{FACE}",
        "concept_id": concept_id,
        "curriculum_tags": [
            concept_id,
            f"surface:{surface}",
            f"slug:{slug}",
            f"face:{FACE}",
            "phonology:meta",
        ],
        "lesson_id": LESSON_ID,
    }


def _letter_frame(*, cue: str, letter: str, concept_id: str, label: str) -> dict:
    role = "vowel" if concept_id.endswith(".vowel") else "consonant"
    fid = f"phonology-letter-{cue}-{role}-{FACE}"
    return {
        "id": fid,
        "path": f"{LESSON_ID}/images/{fid}.jpg",
        "scene_label": f"card:phonology:letter:{cue}:{role}:{FACE}",
        "concept_id": concept_id,
        "curriculum_tags": [
            concept_id,
            f"surface:{letter}",
            f"cue:{cue}",
            f"face:{FACE}",
            f"phonology:{role}",
            "phonology:letter_class",
        ],
        "lesson_id": LESSON_ID,
    }


def build_frames(*, vowel_cues: set[str], all_letters: bool) -> list[dict]:
    by_cue = _cyrl_by_cue()
    frames: list[dict] = [
        _category_frame(
            fid=f"meta-phonology-vowel-{FACE}",
            surface=LABEL_VOWEL,
            concept_id=META_VOWEL,
            slug="phonology-vowel",
        ),
        _category_frame(
            fid=f"meta-phonology-consonant-{FACE}",
            surface=LABEL_CONSONANT,
            concept_id=META_CONSONANT,
            slug="phonology-consonant",
        ),
    ]
    cues = sorted(by_cue.keys()) if all_letters else sorted(vowel_cues | {"m", "k", "s", "t"})
    for cue in cues:
        if cue not in by_cue:
            continue
        _, lo, _ = by_cue[cue]
        if cue in vowel_cues:
            frames.append(
                _letter_frame(
                    cue=cue,
                    letter=lo,
                    concept_id=META_VOWEL,
                    label=LABEL_VOWEL,
                )
            )
        elif all_letters or cue in {"m", "k", "s", "t"}:
            frames.append(
                _letter_frame(
                    cue=cue,
                    letter=lo,
                    concept_id=META_CONSONANT,
                    label=LABEL_CONSONANT,
                )
            )
    return frames


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vowel-list", type=Path, default=VOWEL_LIST)
    p.add_argument(
        "--all-letters",
        action="store_true",
        help="все 33 буквы (lower); иначе категории + пилот 10 букв",
    )
    args = p.parse_args()

    vowel_cues = _load_vowel_cues(args.vowel_list)
    frames = build_frames(vowel_cues=vowel_cues, all_letters=args.all_letters)

    img_dir = ROOT / LESSON_ID / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    by_cue = _cyrl_by_cue()

    for fr in frames:
        fid = str(fr["id"])
        out = img_dir / f"{fid}.jpg"
        if fid.startswith("meta-phonology-"):
            surface = LABEL_VOWEL if "vowel" in fid else LABEL_CONSONANT
            draw_text_centered(surface, out, size=120)
            continue
        tags = {t.split(":", 1)[0]: t.split(":", 1)[1] for t in fr.get("curriculum_tags") or [] if ":" in t}
        cue = tags.get("cue", "")
        letter = tags.get("surface", by_cue.get(cue, ("", "", ""))[1])
        label = LABEL_VOWEL if fr["concept_id"] == META_VOWEL else LABEL_CONSONANT
        draw_letter_with_label(letter, label, out)

    merge_manifest(
        frames,
        stage_id=STAGE_ID,
        stage_title=STAGE_TITLE,
        stage_order=STAGE_ORDER,
        lesson_id=LESSON_ID,
    )
    print(
        json.dumps(
            {
                "lesson": LESSON_ID,
                "stage": STAGE_ID,
                "frames": len(frames),
                "vowel_cues": len(vowel_cues),
                "all_letters": args.all_letters,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
