#!/usr/bin/env python3
"""Build field-native RU ABC cards (letter + synthetic anchor + word label)."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
CARD_W, CARD_H = 640, 480
BG = (252, 251, 246)
INK = (28, 28, 32)
ACCENT = (55, 95, 175)


def _blank() -> Image.Image:
    return Image.new("RGB", (CARD_W, CARD_H), BG)


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = ("arialbd.ttf", "arial.ttf") if bold else ("arial.ttf", "arialbd.ttf")
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_anchor(draw: ImageDraw.ImageDraw, kind: str, cx: int, cy: int) -> None:
    s = 1.0
    if kind == "arc":
        draw.arc((cx - 90, cy - 20, cx + 90, cy + 100), 200, 340, fill=INK, width=8)
    elif kind == "two_dots":
        for dx in (-45, 45):
            draw.ellipse((cx + dx - 18, cy - 18, cx + dx + 18, cy + 18), fill=INK)
    elif kind == "circle":
        draw.ellipse((cx - 70, cy - 70, cx + 70, cy + 70), outline=INK, width=7)
    elif kind == "letter_ve":
        # две грани как у буквы В (не путать с О-круг)
        draw.line((cx - 65, cy + 55, cx, cy - 55), fill=INK, width=8)
        draw.line((cx, cy - 55, cx + 65, cy + 55), fill=INK, width=8)
    elif kind == "corner":
        draw.line((cx - 70, cy + 60, cx - 70, cy - 50, cx + 50, cy - 50), fill=INK, width=7)
    elif kind == "house":
        draw.polygon(
            [(cx, cy - 75), (cx + 80, cy - 10), (cx + 80, cy + 70), (cx - 80, cy + 70), (cx - 80, cy - 10)],
            outline=INK,
        )
        draw.line((cx - 80, cy - 10, cx, cy - 75, cx + 80, cy - 10), fill=INK, width=7)
    elif kind == "three_lines":
        for dy in (-40, 0, 40):
            draw.line((cx - 80, cy + dy, cx + 80, cy + dy), fill=INK, width=6)
    elif kind == "e_two_dots":
        for dy in (-35, 0, 35):
            draw.line((cx - 70, cy + dy, cx + 55, cy + dy), fill=INK, width=5)
        draw.line((cx - 70, cy - 35, cx - 70, cy + 35), fill=INK, width=5)
        for dx in (-20, 20):
            draw.ellipse((cx + dx - 8, cy - 95, cx + dx + 8, cy - 79), fill=INK)
    elif kind == "star3":
        for ang in (90, 210, 330):
            import math

            rad = math.radians(ang)
            x2 = cx + int(75 * math.cos(rad))
            y2 = cy + int(75 * math.sin(rad))
            draw.line((cx, cy, x2, y2), fill=INK, width=6)
    elif kind == "zigzag":
        pts = [(cx - 80, cy), (cx - 30, cy - 50), (cx + 20, cy + 50), (cx + 70, cy - 40)]
        draw.line(pts, fill=INK, width=6)
    elif kind == "bridge":
        draw.line((cx - 70, cy + 50, cx - 70, cy - 40), fill=INK, width=6)
        draw.line((cx + 70, cy + 50, cx + 70, cy - 40), fill=INK, width=6)
        draw.line((cx - 70, cy - 40, cx + 70, cy - 40), fill=INK, width=6)
    elif kind == "bridge_dot":
        _draw_anchor(draw, "bridge", cx, cy)
        draw.ellipse((cx + 55, cy - 75, cx + 71, cy - 59), fill=INK)
    elif kind == "angle_k":
        draw.line((cx - 60, cy + 60, cx - 60, cy - 60, cx + 70, cy - 10), fill=INK, width=7)
    elif kind == "angle_l":
        draw.line((cx + 60, cy + 60, cx + 60, cy - 60, cx - 70, cy - 10), fill=INK, width=7)
    elif kind == "mountain":
        draw.line((cx - 90, cy + 60, cx - 30, cy - 60, cx + 30, cy + 10, cx + 90, cy + 60), fill=INK, width=6)
    elif kind == "gate":
        draw.line((cx - 70, cy + 60, cx - 70, cy - 60, cx + 70, cy - 60, cx + 70, cy + 60), fill=INK, width=7)
    elif kind == "ring":
        draw.ellipse((cx - 85, cy - 85, cx + 85, cy + 85), outline=INK, width=8)
    elif kind == "p_loop":
        draw.line((cx - 50, cy + 60, cx - 50, cy - 60), fill=INK, width=7)
        draw.arc((cx - 50, cy - 60, cx + 40, cy + 20), 270, 90, fill=INK, width=7)
    elif kind == "c_curve":
        draw.arc((cx - 60, cy - 60, cx + 60, cy + 60), 45, 315, fill=INK, width=8)
    elif kind == "t_bar":
        draw.line((cx, cy - 60, cx, cy + 60), fill=INK, width=7)
        draw.line((cx - 70, cy - 60, cx + 70, cy - 60), fill=INK, width=7)
    elif kind == "u_cup":
        draw.arc((cx - 70, cy - 40, cx + 70, cy + 80), 180, 360, fill=INK, width=7)
    elif kind == "phi":
        draw.ellipse((cx - 70, cy - 70, cx + 10, cy + 10), outline=INK, width=6)
        draw.ellipse((cx - 10, cy - 70, cx + 70, cy + 10), outline=INK, width=6)
    elif kind == "cross":
        draw.line((cx - 60, cy - 60, cx + 60, cy + 60), fill=INK, width=7)
        draw.line((cx + 60, cy - 60, cx - 60, cy + 60), fill=INK, width=7)
    elif kind == "box_tail":
        draw.rectangle((cx - 70, cy - 50, cx + 40, cy + 50), outline=INK, width=6)
        draw.line((cx + 40, cy, cx + 85, cy + 35), fill=INK, width=6)
    elif kind == "cup":
        draw.arc((cx - 55, cy - 30, cx + 55, cy + 70), 180, 360, fill=INK, width=7)
    elif kind == "w_shape":
        draw.line((cx - 90, cy - 40, cx - 45, cy + 50, cx, cy - 20, cx + 45, cy + 50, cx + 90, cy - 40), fill=INK, width=6)
    elif kind == "w_tail":
        _draw_anchor(draw, "w_shape", cx, cy - 15)
        draw.line((cx + 90, cy - 55, cx + 110, cy + 20), fill=INK, width=6)
    elif kind == "two_vert":
        for dx in (-35, 35):
            draw.ellipse((cx + dx - 14, cy - 14, cx + dx + 14, cy + 14), fill=INK)
    elif kind == "e_rev":
        for dy in (-35, 0, 35):
            draw.line((cx - 55, cy + dy, cx + 70, cy + dy), fill=INK, width=5)
        draw.line((cx + 70, cy - 35, cx + 70, cy + 35), fill=INK, width=5)
    elif kind == "yo_circle":
        draw.ellipse((cx - 55, cy - 25, cx + 55, cy + 85), outline=INK, width=6)
        draw.line((cx, cy + 85, cx, cy + 110), fill=INK, width=6)
    elif kind == "ya_bowl":
        draw.arc((cx - 60, cy - 30, cx + 60, cy + 90), 200, 340, fill=INK, width=7)
        draw.line((cx - 60, cy + 10, cx - 60, cy - 70), fill=INK, width=7)
    elif kind == "one_dot":
        draw.ellipse((cx - 20, cy - 20, cx + 20, cy + 20), fill=INK)
    elif kind == "grid2":
        for i in range(2):
            for j in range(2):
                x = cx - 40 + i * 45
                y = cy - 40 + j * 45
                draw.rectangle((x, y, x + 35, y + 35), outline=INK, width=4)
    else:
        draw.ellipse((cx - 40, cy - 40, cx + 40, cy + 40), outline=ACCENT, width=5)


# grapheme lower, letter upper, word, anchor kind, lesson split
ABC: list[tuple[str, str, str, str, str]] = [
    ("а", "А", "арка", "arc", "lesson-01-a-ya"),
    ("б", "Б", "два", "two_dots", "lesson-01-a-ya"),
    ("в", "В", "вверх", "letter_ve", "lesson-01-a-ya"),
    ("г", "Г", "угол", "corner", "lesson-01-a-ya"),
    ("д", "Д", "дом", "house", "lesson-01-a-ya"),
    ("е", "Е", "три", "three_lines", "lesson-01-a-ya"),
    ("ё", "Ё", "ёж", "e_two_dots", "lesson-01-a-ya"),
    ("ж", "Ж", "лучи", "star3", "lesson-01-a-ya"),
    ("з", "З", "зигзаг", "zigzag", "lesson-01-a-ya"),
    ("и", "И", "мост", "bridge", "lesson-01-a-ya"),
    ("й", "Й", "йод", "bridge_dot", "lesson-01-a-ya"),
    ("к", "К", "клин", "angle_k", "lesson-01-a-ya"),
    ("л", "Л", "луч", "angle_l", "lesson-01-a-ya"),
    ("м", "М", "гора", "mountain", "lesson-01-a-ya"),
    ("н", "Н", "на", "gate", "lesson-01-a-ya"),
    ("о", "О", "око", "ring", "lesson-01-a-ya"),
    ("п", "П", "порог", "gate", "lesson-01-a-ya"),
    ("р", "Р", "рак", "p_loop", "lesson-01-a-ya"),
    ("с", "С", "серп", "c_curve", "lesson-01-a-ya"),
    ("т", "Т", "три", "t_bar", "lesson-01-a-ya"),
    ("у", "У", "узор", "u_cup", "lesson-01-a-ya"),
    ("ф", "Ф", "фиг", "phi", "lesson-01-a-ya"),
    ("х", "Х", "крест", "cross", "lesson-01-a-ya"),
    ("ц", "Ц", "цеп", "box_tail", "lesson-01-a-ya"),
    ("ч", "Ч", "чаша", "cup", "lesson-01-a-ya"),
    ("ш", "Ш", "шаг", "w_shape", "lesson-01-a-ya"),
    ("щ", "Щ", "щит", "w_tail", "lesson-01-a-ya"),
    ("ъ", "Ъ", "твёрдый", "one_dot", "lesson-01-a-ya"),
    ("ы", "Ы", "два", "two_vert", "lesson-01-a-ya"),
    ("ь", "Ь", "мягкий", "c_curve", "lesson-01-a-ya"),
    ("э", "Э", "эхо", "e_rev", "lesson-01-a-ya"),
    ("ю", "Ю", "юла", "yo_circle", "lesson-01-a-ya"),
    ("я", "Я", "яма", "ya_bowl", "lesson-01-a-ya"),
]


def draw_letter_card(gr: str, letter: str, word: str, anchor: str, out: Path) -> None:
    img = _blank()
    draw = ImageDraw.Draw(img)
    lf = _font(120, bold=True)
    wf = _font(36)
    draw.text((36, 24), letter, fill=ACCENT, font=lf)
    _draw_anchor(draw, anchor, CARD_W // 2, CARD_H // 2 + 10)
    bbox = draw.textbbox((0, 0), word, font=wf)
    tw = bbox[2] - bbox[0]
    draw.text((CARD_W // 2 - tw // 2, CARD_H - 72), word, fill=INK, font=wf)
    img.save(out, "JPEG", quality=92)


def frame_id(gr: str, word: str) -> str:
    safe = gr if gr.isalnum() else "y"
    return f"letter-{safe}-{word[:16].replace(' ', '-')}"


def manifest_frames() -> list[dict]:
    frames: list[dict] = []
    for gr, letter, word, anchor, lesson_id in ABC:
        fid = frame_id(gr, word)
        frames.append(
            {
                "id": fid,
                "path": f"{lesson_id}/images/{fid}.jpg",
                "scene_label": f"card:letter:{letter}:{word}",
                "lesson_id": lesson_id,
                "letter": letter,
                "grapheme": gr,
                "word": word,
                "anchor": anchor,
                "concept_id": f"grapheme.cyrl.{gr}",
                "curriculum_tags": ["lex.grapheme.cyrl", f"lex.word.{word}"],
            }
        )
    return frames


def write_manifest() -> None:
    manifest = {
        "schema_version": 1,
        "class_id": "lexical-cards-ru",
        "class_kind": "lexical",
        "target_agent": "von-neumann",
        "tract_id": "visual",
        "companion_tract": "alphabet-ru",
        "codec_id": "retinal_lrgb",
        "ingest_cli": "casa.cli.ingest_lesson_moment",
        "_note": "letter/word/anchor — lab authoring only; не oracle на predict",
        "stages": [
            {
                "id": "stage-01-a-ya",
                "title": "Букварь: А–Я (field-native якоря)",
                "order": 1,
                "lesson_ids": ["lesson-01-a-ya"],
            }
        ],
        "frames": manifest_frames(),
    }
    (ROOT / "class.manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    built: list[str] = []
    for gr, letter, word, anchor, lesson_id in ABC:
        img_dir = ROOT / lesson_id / "images"
        img_dir.mkdir(parents=True, exist_ok=True)
        fname = f"{frame_id(gr, word)}.jpg"
        path = img_dir / fname
        draw_letter_card(gr, letter, word, anchor, path)
        built.append(str(path.relative_to(ROOT)).replace("\\", "/"))
    write_manifest()
    print(json.dumps({"built": len(built), "manifest": "class.manifest.json"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
