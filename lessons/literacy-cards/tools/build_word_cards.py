#!/usr/bin/env python3
"""Whole-word cards + manifest merge (pilot or corpus wordlist)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from literacy_render import draw_text_centered  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FACE = "sans"

PILOT: list[tuple[str, str]] = [
    ("mama", "мама"),
    ("papa", "папа"),
    ("kot", "кот"),
    ("dom", "дом"),
    ("sok", "сок"),
    ("mir", "мир"),
    ("ruka", "рука"),
    ("voda", "вода"),
]

LATIN_SLUG = re.compile(r"^[a-z][a-z0-9_-]*$")


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s.strip())


def slug_for_surface(surface: str) -> str:
    s = _nfc(surface).lower()
    if LATIN_SLUG.fullmatch(s.replace("_", "")):
        return s.replace(" ", "_")[:32]
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]


def word_concept_id(slug: str) -> str:
    return f"lang.word.{slug}"


def word_frame_id(slug: str, *, face: str = FACE) -> str:
    return f"word-{slug}-{face}"


def build_frames(
    pairs: list[tuple[str, str]],
    *,
    lesson_id: str,
    face: str = FACE,
    closed_class: bool = False,
) -> list[dict]:
    frames: list[dict] = []
    for slug, surface in pairs:
        fid = word_frame_id(slug, face=face)
        cid = word_concept_id(slug)
        tags = [cid, f"word:{surface}", f"slug:{slug}", f"face:{face}"]
        if closed_class:
            tags.append("closed-class")
        frames.append(
            {
                "id": fid,
                "path": f"{lesson_id}/images/{fid}.jpg",
                "scene_label": f"card:word:{slug}:{face}",
                "concept_id": cid,
                "curriculum_tags": tags,
                "lesson_id": lesson_id,
            }
        )
    return frames


def merge_manifest(
    frames: list[dict],
    *,
    stage_id: str,
    stage_title: str,
    stage_order: int,
    lesson_id: str,
) -> None:
    manifest_path = ROOT / "class.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not any(s.get("id") == stage_id for s in manifest.get("stages") or []):
        manifest.setdefault("stages", []).append(
            {
                "id": stage_id,
                "title": stage_title,
                "order": stage_order,
                "lesson_ids": [lesson_id],
            }
        )
        manifest["stages"].sort(key=lambda s: int(s.get("order") or 0))
    ids = {str(f.get("id")) for f in manifest.get("frames") or []}
    for fr in frames:
        if fr["id"] not in ids:
            manifest.setdefault("frames", []).append(fr)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


CLOSED_CLASS_WORDLIST = ROOT / "data" / "ru-closed-class-v1.txt"


def _font_size(surface: str) -> int:
    n = len(surface)
    if n <= 2:
        return 220
    if n <= 4:
        return 200
    if n <= 8:
        return 150
    return 120


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--wordlist", type=Path, default=None, help="One word per line (corpus)")
    p.add_argument("--limit", type=int, default=500)
    p.add_argument("--pilot", action="store_true", help="8 pilot words only")
    p.add_argument(
        "--closed-class",
        action="store_true",
        help="closed-class slice (ADR-0030 L1b) from data/ru-closed-class-v1.txt",
    )
    args = p.parse_args()

    closed_class = bool(args.closed_class)
    if args.closed_class:
        wordlist = args.wordlist or CLOSED_CLASS_WORDLIST
        lesson_id = "lesson-07-closed-class"
        stage_id = "stage-07-closed-class"
        stage_title = "Закрытый класс (служебные слова)"
        stage_order = 79
        words = [_nfc(ln) for ln in wordlist.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if args.limit > 0:
            words = words[: args.limit]
        pairs = [(slug_for_surface(w), w) for w in words]
    elif args.pilot or args.wordlist is None:
        lesson_id = "lesson-03-words-cyrl"
        pairs = list(PILOT)
        stage_id = "stage-03-words-cyrl"
        stage_title = "Слова целиком (кириллица)"
        stage_order = 3
    else:
        lesson_id = "lesson-06-words-cyrl-corpus"
        words = [
            _nfc(ln)
            for ln in args.wordlist.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ][: args.limit]
        pairs = [(slug_for_surface(w), w) for w in words]
        stage_id = "stage-06-words-cyrl-corpus"
        stage_title = "Корпус РЯ (частотные слова)"
        stage_order = 6

    img_dir = ROOT / lesson_id / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    for slug, surface in pairs:
        draw_text_centered(surface, img_dir / f"{word_frame_id(slug)}.jpg", size=_font_size(surface))

    frames = build_frames(pairs, lesson_id=lesson_id, closed_class=closed_class)
    merge_manifest(
        frames,
        stage_id=stage_id,
        stage_title=stage_title,
        stage_order=stage_order,
        lesson_id=lesson_id,
    )
    print(
        json.dumps(
            {"lesson": lesson_id, "stage": stage_id, "words": len(pairs)},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
