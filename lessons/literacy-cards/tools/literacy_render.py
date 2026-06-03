"""Shared JPEG render for literacy cards."""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CARD_W, CARD_H = 640, 480
BG = (250, 250, 248)
_FONT_CACHE: dict[int, ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}


def font_paths() -> list[Path | str]:
    paths: list[Path | str] = []
    if os.name == "nt":
        fonts = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Fonts"
        paths.extend([fonts / "segoeui.ttf", fonts / "arial.ttf"])
    paths.extend(["arial.ttf", "DejaVuSans.ttf"])
    return paths


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if size in _FONT_CACHE:
        return _FONT_CACHE[size]
    for path in font_paths():
        try:
            loaded = ImageFont.truetype(str(path), size)
        except OSError:
            continue
        _FONT_CACHE[size] = loaded
        return loaded
    loaded = ImageFont.load_default()
    _FONT_CACHE[size] = loaded
    return loaded


def draw_text_centered(text: str, out: Path, *, size: int) -> None:
    img = Image.new("RGB", (CARD_W, CARD_H), BG)
    draw = ImageDraw.Draw(img)
    fnt = font(size)
    bbox = draw.textbbox((0, 0), text, font=fnt)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (CARD_W - tw) // 2 - bbox[0]
    y = (CARD_H - th) // 2 - bbox[1]
    draw.text((x, y), text, fill=(25, 25, 25), font=fnt)
    img.save(out, "JPEG", quality=92)
