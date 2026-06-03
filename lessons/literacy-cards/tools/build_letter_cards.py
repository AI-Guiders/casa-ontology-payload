#!/usr/bin/env python3
"""Build literacy card JPEGs + class.manifest.json (Cyrillic, register lower/upper)."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
CARD_W, CARD_H = 640, 480
BG = (250, 250, 248)
FACE_DEFAULT = "sans"

# (cue_slug, lower, upper) — cue латинский slug для concept_id; на кадре только буква
CYRILLIC: list[tuple[str, str, str]] = [
    ("a", "а", "А"),
    ("b", "б", "Б"),
    ("v", "в", "В"),
    ("g", "г", "Г"),
    ("d", "д", "Д"),
    ("e", "е", "Е"),
    ("yo", "ё", "Ё"),
    ("zh", "ж", "Ж"),
    ("z", "з", "З"),
    ("i", "и", "И"),
    ("j", "й", "Й"),
    ("k", "к", "К"),
    ("l", "л", "Л"),
    ("m", "м", "М"),
    ("n", "н", "Н"),
    ("o", "о", "О"),
    ("p", "п", "П"),
    ("r", "р", "Р"),
    ("s", "с", "С"),
    ("t", "т", "Т"),
    ("u", "у", "У"),
    ("f", "ф", "Ф"),
    ("h", "х", "Х"),
    ("ts", "ц", "Ц"),
    ("ch", "ч", "Ч"),
    ("sh", "ш", "Ш"),
    ("sch", "щ", "Щ"),
    ("hard", "ъ", "Ъ"),
    ("y", "ы", "Ы"),
    ("soft", "ь", "Ь"),
    ("eh", "э", "Э"),
    ("yu", "ю", "Ю"),
    ("ya", "я", "Я"),
]

_FONT_CACHE: dict[tuple[bool, int], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}


def _font_paths() -> list[Path | str]:
    import os

    paths: list[Path | str] = []
    if os.name == "nt":
        fonts = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Fonts"
        paths.extend([fonts / "segoeui.ttf", fonts / "arial.ttf"])
    paths.extend(["arial.ttf", "DejaVuSans.ttf"])
    return paths


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    key = (False, size)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    for path in _font_paths():
        try:
            loaded = ImageFont.truetype(str(path), size)
        except OSError:
            continue
        _FONT_CACHE[key] = loaded
        return loaded
    loaded = ImageFont.load_default()
    _FONT_CACHE[key] = loaded
    return loaded


def grapheme_concept_id(cue: str, register: str) -> str:
    return f"grapheme.cyrl.{cue}.{register}"


def frame_id(cue: str, register: str, *, face: str = FACE_DEFAULT) -> str:
    return f"letter-{cue}-{register}-{face}"


def _draw_letter(letter: str, out: Path, *, size: int = 280) -> None:
    img = Image.new("RGB", (CARD_W, CARD_H), BG)
    draw = ImageDraw.Draw(img)
    font = _font(size)
    bbox = draw.textbbox((0, 0), letter, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (CARD_W - tw) // 2 - bbox[0]
    y = (CARD_H - th) // 2 - bbox[1]
    draw.text((x, y), letter, fill=(25, 25, 25), font=font)
    img.save(out, "JPEG", quality=92)


def build_manifest(*, face: str = FACE_DEFAULT) -> dict:
    frames: list[dict] = []
    for cue, lower, upper in CYRILLIC:
        for register, glyph in (("lower", lower), ("upper", upper)):
            fid = frame_id(cue, register, face=face)
            rel = f"lesson-01-letters-cyrl/images/{fid}.jpg"
            cid = grapheme_concept_id(cue, register)
            frames.append(
                {
                    "id": fid,
                    "path": rel,
                    "scene_label": f"card:letter:{cue}:{register}:{face}",
                    "concept_id": cid,
                    "curriculum_tags": [cid, f"register:{register}", f"cue:{cue}", f"face:{face}"],
                    "lesson_id": "lesson-01-letters-cyrl",
                }
            )
    return {
        "schema_version": 1,
        "class_id": "literacy-cards",
        "target_agent": "von-neumann",
        "tract_id": "visual",
        "codec_id": "retinal_lrgb",
        "ingest_cli": "casa.cli.ingest_visual_class",
        "_note": "vis↔grapheme via lesson_moment lexical step + sleep (bridge_lex)",
        "stages": [
            {
                "id": "stage-01-grapheme-cyrl",
                "title": "Буквы: кириллица, lower/upper",
                "order": 1,
                "lesson_ids": ["lesson-01-letters-cyrl"],
            }
        ],
        "frames": frames,
    }


def main() -> None:
    img_dir = ROOT / "lesson-01-letters-cyrl" / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    built: list[str] = []
    for cue, lower, upper in CYRILLIC:
        for register, glyph in (("lower", lower), ("upper", upper)):
            fname = f"{frame_id(cue, register)}.jpg"
            path = img_dir / fname
            _draw_letter(glyph, path)
            built.append(str(path.relative_to(ROOT)).replace("\\", "/"))

    manifest = build_manifest()
    (ROOT / "class.manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"built": len(built), "frames": len(manifest["frames"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
