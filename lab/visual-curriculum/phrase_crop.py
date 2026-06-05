"""Phrase JPEG → per-word crop helpers (P1 compose probes)."""

from __future__ import annotations

from typing import Any


def render_phrase_rgb(phrase: str, font_pt: int) -> Any:
    from font_legibility_lab import render_word_rgb

    return render_word_rgb(phrase, font_pt)


def phrase_word_boxes(phrase: str, font_pt: int) -> list[dict[str, Any]]:
    """Per-word bounding boxes in centered phrase render."""
    from literacy_render import CARD_H, CARD_W, font
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (CARD_W, CARD_H), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    fnt = font(font_pt)

    bbox_full = draw.textbbox((0, 0), phrase, font=fnt)
    tw, th = bbox_full[2] - bbox_full[0], bbox_full[3] - bbox_full[1]
    x0 = (CARD_W - tw) // 2 - bbox_full[0]
    y0 = (CARD_H - th) // 2 - bbox_full[1]

    out: list[dict[str, Any]] = []
    i = 0
    n = len(phrase)
    while i < n:
        while i < n and phrase[i].isspace():
            i += 1
        if i >= n:
            break
        j = i
        while j < n and not phrase[j].isspace():
            j += 1
        word = phrase[i:j]

        prefix = phrase[:i]
        prefix_plus = phrase[:j]
        x1 = int(x0 + draw.textlength(prefix, font=fnt))
        x2 = int(x0 + draw.textlength(prefix_plus, font=fnt))
        bb = draw.textbbox((x1, y0), word, font=fnt)
        out.append({"word": word, "start": i, "end": j, "bbox": [bb[0], bb[1], bb[2], bb[3]]})
        i = j

    return out


def crop_word_rgb(
    phrase_rgb: Any,
    bbox: list[int],
    *,
    pad: int = 10,
    upscale: bool = True,
) -> Any:
    from casa.sensory.rgb_frame import RgbFrame
    from literacy_render import BG, CARD_H, CARD_W
    from PIL import Image

    x1, y1, x2, y2 = bbox
    x1 = max(0, x1 - pad)
    y1 = max(0, y1 - pad)
    if not isinstance(phrase_rgb, RgbFrame):
        raise TypeError(f"expected RgbFrame, got {type(phrase_rgb)!r}")
    pil = Image.frombytes("RGB", (phrase_rgb.width, phrase_rgb.height), phrase_rgb.rgb)
    crop = pil.crop((x1, y1, min(pil.width, x2 + pad), min(pil.height, y2 + pad)))

    if upscale and crop.width > 0 and crop.height > 0:
        max_w = CARD_W - 40
        max_h = CARD_H - 40
        scale = min(max_w / crop.width, max_h / crop.height)
        if scale > 1.0:
            crop = crop.resize(
                (max(1, int(round(crop.width * scale))), max(1, int(round(crop.height * scale)))),
                resample=Image.Resampling.BICUBIC,
            )

    bg = Image.new("RGB", (CARD_W, CARD_H), BG)
    cx = (CARD_W - crop.width) // 2
    cy = (CARD_H - crop.height) // 2
    bg.paste(crop, (cx, cy))
    return RgbFrame(width=CARD_W, height=CARD_H, rgb=bg.tobytes())
