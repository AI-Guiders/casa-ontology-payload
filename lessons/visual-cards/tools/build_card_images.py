#!/usr/bin/env python3
"""Download CC0/PD assets and build visual curriculum card JPEGs."""

from __future__ import annotations

import io
import json
import math
import os
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
CARD_W, CARD_H = 640, 480
BG = (250, 250, 248)

def _commons_url(file_title: str) -> str:
    q = urllib.parse.urlencode(
        {
            "action": "query",
            "titles": file_title,
            "prop": "imageinfo",
            "iiprop": "url",
            "format": "json",
        }
    )
    req = urllib.request.Request(
        f"https://commons.wikimedia.org/w/api.php?{q}",
        headers={"User-Agent": "casa-visual-cards/1.0 (curriculum build)"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.load(resp)
    page = next(iter(data["query"]["pages"].values()))
    info = page.get("imageinfo") or []
    if not info or "url" not in info[0]:
        raise RuntimeError(f"no url for {file_title}")
    return str(info[0]["url"])


ASSETS = {
    "rice_grain": "File:Single_grain_of_rice.png",
    "cow": "File:Spot_the_cow.png",
}


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "casa-visual-cards/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def _load_raster(raw: bytes) -> Image.Image:
    return Image.open(io.BytesIO(raw)).convert("RGBA")


def _blank() -> Image.Image:
    return Image.new("RGB", (CARD_W, CARD_H), BG)


def _paste_centered(base: Image.Image, sprite: Image.Image, xy: tuple[int, int], size: int) -> None:
    s = sprite.copy()
    s.thumbnail((size, size), Image.Resampling.LANCZOS)
    x = xy[0] - s.width // 2
    y = xy[1] - s.height // 2
    base.paste(s, (x, y), s)


def _draw_dots(n: int, out: Path) -> None:
    img = _blank()
    draw = ImageDraw.Draw(img)
    r = 28
    gap = 120
    cx = CARD_W // 2 - (n - 1) * gap // 2
    cy = CARD_H // 2
    for i in range(n):
        x = cx + i * gap
        draw.ellipse((x - r, cy - r, x + r, cy + r), fill=(20, 20, 20))
    img.save(out, "JPEG", quality=92)


def _centered_box(cx: int, cy: int, half_w: int, half_h: int) -> tuple[int, int, int, int]:
    return (cx - half_w, cy - half_h, cx + half_w, cy + half_h)


def _draw_one_shape(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    kind: str,
    *,
    scale: float = 1.0,
    stroke: tuple[int, int, int] = (25, 25, 25),
    stroke_w: int = 6,
) -> None:
    if kind == "circle":
        r = int(55 * scale)
        draw.ellipse(_centered_box(cx, cy, r, r), outline=stroke, width=stroke_w)
    elif kind == "square":
        half = int(55 * scale)
        draw.rectangle(_centered_box(cx, cy, half, half), outline=stroke, width=stroke_w)
    elif kind == "rectangle":
        draw.rectangle(
            _centered_box(cx, cy, int(70 * scale), int(40 * scale)),
            outline=stroke,
            width=stroke_w,
        )
    else:
        raise ValueError(kind)


def _draw_shape_row(n: int, kind: str, out: Path) -> None:
    img = _blank()
    draw = ImageDraw.Draw(img)
    scale = {2: 1.0, 3: 0.9, 4: 0.78, 5: 0.66}[n]
    gap = {2: 190, 3: 145, 4: 118, 5: 98}[n]
    cy = CARD_H // 2
    start_x = CARD_W // 2 - (n - 1) * gap // 2
    for i in range(n):
        _draw_one_shape(draw, start_x + i * gap, cy, kind, scale=scale)
    img.save(out, "JPEG", quality=92)


def _draw_mini_shape(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    kind: str,
    *,
    size: int = 14,
    stroke: tuple[int, int, int] = (25, 25, 25),
    stroke_w: int = 3,
) -> None:
    scale = size / 55.0
    _draw_one_shape(draw, cx, cy, kind, scale=scale, stroke=stroke, stroke_w=stroke_w)


def _draw_count_term_glyph(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    n: int,
    kind: str,
    *,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> int:
    """Draw `n` + mini shape glyph; return x after term."""
    stroke = (25, 25, 25)
    num = str(n)
    draw.text((x, y), num, fill=stroke, font=font)
    bbox = draw.textbbox((x, y), num, font=font)
    gx = bbox[2] + 18
    gy = y + (bbox[3] - bbox[1]) // 2 + 5
    _draw_mini_shape(draw, gx, gy, kind, size=14)
    return gx + 22


def _shape_half_extents(kind: str, scale: float) -> tuple[int, int]:
    if kind == "circle":
        r = int(55 * scale)
        return r, r
    if kind == "square":
        half = int(55 * scale)
        return half, half
    if kind == "rectangle":
        return int(70 * scale), int(40 * scale)
    raise ValueError(kind)


def _group_row_xs(kind: str, n: int, *, scale: float, center_x: int, edge_gap: int = 30) -> list[int]:
    """Center x for each shape in a row — clear gap between outlines."""
    half_w, _ = _shape_half_extents(kind, scale)
    gap = edge_gap + (6 if kind == "rectangle" else 0)
    pitch = 2 * half_w + gap
    start_x = center_x - (n - 1) * pitch // 2
    return [start_x + i * pitch for i in range(n)]


def _group_span_width(kind: str, n: int, scale: float) -> tuple[int, int]:
    """Total width and max half-height for a row group centered at 0."""
    xs = _group_row_xs(kind, n, scale=scale, center_x=0)
    half_w, half_h = _shape_half_extents(kind, scale)
    left = min(xs) - half_w
    right = max(xs) + half_w
    return right - left, half_h


def _count_term_width(
    draw: ImageDraw.ImageDraw,
    n: int,
    kind: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> int:
    bbox = draw.textbbox((0, 0), str(n), font=font)
    return bbox[2] - bbox[0] + 40


def _draw_mixed_shape_counts(out: Path, *, show_label: bool = False) -> None:
    """3 circles + 2 squares + 2 rectangles in separate groups; optional n(shape) label."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    stroke = (25, 25, 25)
    groups: list[tuple[str, int, float]] = [
        ("circle", 3, 0.36),
        ("square", 2, 0.40),
        ("rectangle", 2, 0.38),
    ]
    sep = (190, 190, 188)
    sep_pad = 56
    cy = CARD_H // 2 - (50 if show_label else 20)

    spans: list[tuple[int, int]] = [_group_span_width(k, n, s) for k, n, s in groups]
    total_w = sum(w for w, _ in spans) + sep_pad * (len(groups) - 1)
    x = (CARD_W - total_w) // 2
    centers: list[int] = []
    for width, _ in spans:
        centers.append(x + width // 2)
        x += width + sep_pad

    for col, (kind, n, scale) in enumerate(groups):
        for sx in _group_row_xs(kind, n, scale=scale, center_x=centers[col]):
            _draw_one_shape(draw, sx, cy, kind, scale=scale, stroke=stroke, stroke_w=5)

    max_h = max(h for _, h in spans)
    for col in range(len(groups) - 1):
        right = centers[col] + spans[col][0] // 2
        left_next = centers[col + 1] - spans[col + 1][0] // 2
        sx = (right + left_next) // 2
        draw.line((sx, cy - max_h - 10, sx, cy + max_h + 10), fill=sep, width=2)

    if show_label:
        label_font = _font(34)
        ly = cy + max_h + 36
        for col, (kind, n, _) in enumerate(groups):
            tw = _count_term_width(draw, n, kind, label_font)
            _draw_count_term_glyph(draw, centers[col] - tw // 2, ly, n, kind, font=label_font)

    img.save(out, "JPEG", quality=92)


def _draw_geom_circle_sized(out: Path, *, diameter: int) -> None:
    """Окружность заданного диаметра (meta size on geom)."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    stroke = (25, 25, 25)
    cx, cy = CARD_W // 2, CARD_H // 2
    if diameter >= 300:
        width = 10
    elif diameter >= 160:
        width = 9
    elif diameter >= 80:
        width = 7
    else:
        width = 5
    draw.ellipse(_centered_box(cx, cy, diameter, diameter), outline=stroke, width=width)
    img.save(out, "JPEG", quality=92)


def _draw_geom_lex_circle(out: Path) -> None:
    """Lesson-15: круг — крупная окружность (контраст с квадратом lex)."""
    _draw_geom_circle_sized(out, diameter=210)


def _draw_two_circles_compare(
    out: Path,
    *,
    left_d: int,
    right_d: int,
    relation: str | None = None,
) -> None:
    """Два круга разного радиуса; relation greater/less — скобка только на левом (S6 pure)."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    stroke = (25, 25, 25)
    cy = CARD_H // 2
    left_cx = CARD_W // 2 - 110
    right_cx = CARD_W // 2 + 110
    for cx, d in ((left_cx, left_d), (right_cx, right_d)):
        w = 9 if d >= 120 else 7
        draw.ellipse(_centered_box(cx, cy, d, d), outline=stroke, width=w)
    rel = (relation or "").strip().lower()
    if rel in ("greater", "less"):
        d = left_d
        half = d // 2
        x_lo = left_cx - half
        x_hi = left_cx + half
        if rel == "greater":
            col = (45, 95, 165)
            br_y = cy - half - 22
            draw.line((x_lo, br_y, x_hi, br_y), fill=col, width=5)
            draw.line((x_lo, br_y, x_lo, br_y + 12), fill=col, width=4)
            draw.line((x_hi, br_y, x_hi, br_y + 12), fill=col, width=4)
        else:
            col = (165, 75, 45)
            br_y = cy + half + 22
            draw.line((x_lo, br_y, x_hi, br_y), fill=col, width=5)
            draw.line((x_lo, br_y, x_lo, br_y - 12), fill=col, width=4)
            draw.line((x_hi, br_y, x_hi, br_y - 12), fill=col, width=4)
    img.save(out, "JPEG", quality=92)


def _draw_geom_circle_center(out: Path) -> None:
    """Круг с точкой в центре → math.geom.center."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    stroke = (25, 25, 25)
    cx, cy = CARD_W // 2, CARD_H // 2
    d = 200
    draw.ellipse(_centered_box(cx, cy, d, d), outline=stroke, width=9)
    r = 8
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=stroke)
    img.save(out, "JPEG", quality=92)


def _draw_geom_circle_radius(out: Path) -> None:
    """Круг, центр и отрезок центр→контур → math.geom.radius."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    stroke = (25, 25, 25)
    cx, cy = CARD_W // 2, CARD_H // 2
    half = 100
    draw.ellipse(_centered_box(cx, cy, half * 2, half * 2), outline=stroke, width=9)
    dot = 6
    draw.ellipse((cx - dot, cy - dot, cx + dot, cy + dot), fill=stroke)
    edge_x = cx + half
    draw.line((cx, cy, edge_x, cy), fill=stroke, width=5)
    draw.ellipse((edge_x - dot, cy - dot, edge_x + dot, cy + dot), fill=stroke)
    img.save(out, "JPEG", quality=92)


def _draw_geom_lex_square(out: Path) -> None:
    """Lesson-15: квадрат — меньше круга, точки в углах (отличие от окружности)."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    stroke = (25, 25, 25)
    cx, cy = CARD_W // 2, CARD_H // 2
    half = 148
    box = _centered_box(cx, cy, half, half)
    draw.rectangle(box, outline=stroke, width=9)
    x0, y0, x1, y1 = box
    r = 6
    for px, py in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        draw.ellipse((px - r, py - r, px + r, py + r), fill=stroke)
    img.save(out, "JPEG", quality=92)


def _draw_shape(kind: str, out: Path) -> None:
    img = _blank()
    draw = ImageDraw.Draw(img)
    stroke = (25, 25, 25)
    stroke_w = 8
    cx, cy = CARD_W // 2, CARD_H // 2
    if kind == "circle":
        r = 180
        draw.ellipse(_centered_box(cx, cy, r, r), outline=stroke, width=stroke_w)
    elif kind == "square":
        half = 180
        draw.rectangle(_centered_box(cx, cy, half, half), outline=stroke, width=stroke_w)
    elif kind == "rectangle":
        draw.rectangle(_centered_box(cx, cy, 240, 140), outline=stroke, width=stroke_w)
    else:
        raise ValueError(kind)
    img.save(out, "JPEG", quality=92)


def _draw_gridded_rect(cols: int, rows: int, out: Path) -> None:
    """cols × rows unit cells; square when cols == rows."""
    _draw_gridded_rect_advanced(cols, rows, out)


def _grid_geometry(cols: int, rows: int) -> tuple[int, int, int, int, int]:
    margin = 56
    cell = min((CARD_W - 2 * margin) // cols, (CARD_H - 2 * margin - 56) // rows)
    grid_w = cols * cell
    grid_h = rows * cell
    x0 = (CARD_W - grid_w) // 2
    y0 = (CARD_H - grid_h) // 2 - 20
    return x0, y0, cell, grid_w, grid_h


def _draw_gridded_rect_advanced(
    cols: int,
    rows: int,
    out: Path,
    *,
    label: str = "",
    fill_cols: tuple[int, int] | None = None,
    fill_rows: tuple[int, int] | None = None,
    fill_color: tuple[int, int, int] = (45, 95, 165),
    strip_divisions: int = 0,
    highlight_strip: int = 0,
) -> None:
    """Grid with optional shaded region, vertical strip partition, and label."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    x0, y0, cell, grid_w, grid_h = _grid_geometry(cols, rows)
    x1 = x0 + grid_w
    y1 = y0 + grid_h
    outer = (25, 25, 25)
    grid_line = (175, 175, 172)

    if fill_cols and fill_rows:
        c0, c1 = fill_cols
        r0, r1 = fill_rows
        draw.rectangle(
            (x0 + c0 * cell, y0 + r0 * cell, x0 + c1 * cell, y0 + r1 * cell),
            fill=fill_color,
        )

    if strip_divisions > 0:
        strip_w = grid_w // strip_divisions
        hi = max(0, min(highlight_strip, strip_divisions - 1))
        sx0 = x0 + hi * strip_w
        sx1 = x0 + (hi + 1) * strip_w if hi < strip_divisions - 1 else x1
        draw.rectangle((sx0, y0, sx1, y1), fill=fill_color, outline=None)
        for k in range(1, strip_divisions):
            x = x0 + k * strip_w
            draw.line((x, y0, x, y1), fill=outer, width=4)

    for c in range(1, cols):
        x = x0 + c * cell
        draw.line((x, y0, x, y1), fill=grid_line, width=2)
    for r in range(1, rows):
        y = y0 + r * cell
        draw.line((x0, y, x1, y), fill=grid_line, width=2)
    draw.rectangle((x0, y0, x1, y1), outline=outer, width=8)

    if label:
        label_font = _font(44)
        bbox = draw.textbbox((0, 0), label, font=label_font)
        tw = bbox[2] - bbox[0]
        draw.text((CARD_W // 2 - tw // 2, y1 + 24), label, fill=(20, 20, 20), font=label_font)
    img.save(out, "JPEG", quality=92)


def _draw_multiply(cols: int, rows: int, out: Path) -> None:
    """Area model: cols × rows unit cells with product label."""
    _draw_gridded_rect_advanced(cols, rows, out, label=f"{cols}×{rows}")


def _draw_division_square(side: int, parts: int, out: Path) -> None:
    """Square side×side partitioned into `parts` equal vertical strips; one strip highlighted."""
    _draw_gridded_rect_advanced(
        side,
        side,
        out,
        label=f"{side}÷{parts}",
        strip_divisions=parts,
        highlight_strip=0,
        fill_color=(165, 75, 45),
    )


def _draw_fraction(numerator: int, denominator: int, out: Path) -> None:
    """d×d cell grid; bottom `numerator` of `denominator` rows shaded (area = n/d)."""
    d = denominator
    _draw_gridded_rect_advanced(
        d,
        d,
        out,
        label=f"{numerator}/{denominator}",
        fill_cols=(0, d),
        fill_rows=(d - numerator, d),
        fill_color=(45, 95, 165),
    )


def _draw_fraction_vertical_strip(side: int, parts: int, out: Path) -> None:
    """Same geometry as division (one vertical strip); label n/d with n=1 — links ÷ and fractions."""
    _draw_gridded_rect_advanced(
        side,
        side,
        out,
        label=f"1/{parts}",
        strip_divisions=parts,
        highlight_strip=0,
        fill_color=(45, 95, 165),
    )


_FONT_CACHE: dict[tuple[bool, int], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}


def _font_paths(*, symbols: bool) -> list[Path | str]:
    paths: list[Path | str] = []
    if os.name == "nt":
        fonts = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Fonts"
        if symbols:
            paths.extend(
                [
                    fonts / "seguisym.ttf",
                    fonts / "SegoeUISymbol.ttf",
                    fonts / "Cambria.ttc",
                    fonts / "cambria.ttc",
                ]
            )
        paths.extend(
            [
                fonts / "segoeui.ttf",
                fonts / "seguiui.ttf",
                fonts / "arial.ttf",
            ]
        )
    paths.extend(["arial.ttf", "DejaVuSans.ttf"])
    return paths


def _font(size: int, *, symbols: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    key = (symbols, size)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    for path in _font_paths(symbols=symbols):
        try:
            if str(path).lower().endswith(".ttc"):
                loaded = ImageFont.truetype(str(path), size, index=0)
            else:
                loaded = ImageFont.truetype(str(path), size)
        except OSError:
            continue
        _FONT_CACHE[key] = loaded
        return loaded
    loaded = ImageFont.load_default()
    _FONT_CACHE[key] = loaded
    return loaded


def _numberline_layout(*, max_n: int = 5, y: int | None = None) -> tuple[int, int, int, float]:
    axis_y = CARD_H // 2 if y is None else y
    x0, x1 = 70, CARD_W - 70
    step = (x1 - x0) / max_n
    return x0, x1, axis_y, step


def _draw_numberline_axis(
    draw: ImageDraw.ImageDraw,
    *,
    max_n: int = 5,
    y: int | None = None,
    font_size: int = 36,
) -> tuple[int, int, float]:
    x0, x1, axis_y, step = _numberline_layout(max_n=max_n, y=y)
    font = _font(font_size)
    draw.line((x0, axis_y, x1, axis_y), fill=(30, 30, 30), width=4)
    for i in range(max_n + 1):
        x = int(x0 + i * step)
        draw.line((x, axis_y - 12, x, axis_y + 12), fill=(30, 30, 30), width=3)
        draw.text((x - 10, axis_y + 18), str(i), fill=(20, 20, 20), font=font)
    return x0, axis_y, step


def _draw_numberline(out: Path) -> None:
    img = _blank()
    draw = ImageDraw.Draw(img)
    _draw_numberline_axis(draw, max_n=3, y=CARD_H // 2 + 40)
    img.save(out, "JPEG", quality=92)


def _draw_numberline_mark(n: int, out: Path, *, max_n: int = 5) -> None:
    img = _blank()
    draw = ImageDraw.Draw(img)
    x0, axis_y, step = _draw_numberline_axis(draw, max_n=max_n, y=CARD_H // 2)
    mx = int(x0 + n * step)
    r = 16
    draw.ellipse((mx - r, axis_y - r, mx + r, axis_y + r), fill=(20, 20, 20))
    img.save(out, "JPEG", quality=92)


def _draw_numberline_compare(a: int, b: int, relation: str, out: Path, *, max_n: int = 5) -> None:
    img = _blank()
    draw = ImageDraw.Draw(img)
    axis_y = CARD_H // 2 - 40
    x0, _, step = _draw_numberline_axis(draw, max_n=max_n, y=axis_y, font_size=32)
    mark = (60, 60, 60)
    for val in (a, b):
        vx = int(x0 + val * step)
        r = 11
        draw.ellipse((vx - r, axis_y - r, vx + r, axis_y + r), fill=mark)
    label = f"{a} > {b}" if relation == "gt" else f"{a} < {b}"
    label_font = _font(44)
    bbox = draw.textbbox((0, 0), label, font=label_font)
    tw = bbox[2] - bbox[0]
    draw.text((CARD_W // 2 - tw // 2, axis_y + 58), label, fill=(20, 20, 20), font=label_font)
    img.save(out, "JPEG", quality=92)


def _draw_numberline_compare_pure_gt(greater: int, lesser: int, out: Path, *, max_n: int = 5) -> None:
    """S1 pure: only > — bracket above axis, arrow at greater tick (no < on card)."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    axis_y = CARD_H // 2 + 24
    x0, _, step = _draw_numberline_axis(draw, max_n=max_n, y=axis_y, font_size=28)
    x_lo = int(x0 + lesser * step)
    x_hi = int(x0 + greater * step)
    col = (45, 95, 165)
    br_y = axis_y - 48
    draw.line((x_lo, br_y, x_hi, br_y), fill=col, width=6)
    draw.line((x_lo, br_y, x_lo, br_y + 14), fill=col, width=4)
    draw.line((x_hi, br_y, x_hi, br_y + 14), fill=col, width=4)
    draw.polygon([(x_hi, br_y), (x_hi + 16, br_y + 9), (x_hi, br_y + 18)], fill=col)
    mark = (70, 70, 70)
    for val in (lesser, greater):
        vx = int(x0 + val * step)
        r = 10
        draw.ellipse((vx - r, axis_y - r, vx + r, axis_y + r), fill=mark)
    label = f"{greater} > {lesser}"
    label_font = _font(42)
    bbox = draw.textbbox((0, 0), label, font=label_font)
    tw = bbox[2] - bbox[0]
    draw.text((CARD_W // 2 - tw // 2, axis_y + 52), label, fill=(20, 20, 20), font=label_font)
    img.save(out, "JPEG", quality=92)


def _draw_numberline_compare_pure_lt(lesser: int, greater: int, out: Path, *, max_n: int = 5) -> None:
    """S1 pure: only < — bracket below axis, arrow at lesser tick (no > on card)."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    axis_y = CARD_H // 2 - 28
    x0, _, step = _draw_numberline_axis(draw, max_n=max_n, y=axis_y, font_size=28)
    x_lo = int(x0 + lesser * step)
    x_hi = int(x0 + greater * step)
    col = (165, 75, 45)
    br_y = axis_y + 48
    draw.line((x_hi, br_y, x_lo, br_y), fill=col, width=6)
    draw.line((x_lo, br_y, x_lo, br_y - 14), fill=col, width=4)
    draw.line((x_hi, br_y, x_hi, br_y - 14), fill=col, width=4)
    draw.polygon([(x_lo, br_y), (x_lo - 16, br_y + 9), (x_lo, br_y + 18)], fill=col)
    mark = (70, 70, 70)
    for val in (lesser, greater):
        vx = int(x0 + val * step)
        r = 10
        draw.ellipse((vx - r, axis_y - r, vx + r, axis_y + r), fill=mark)
    label = f"{lesser} < {greater}"
    label_font = _font(42)
    bbox = draw.textbbox((0, 0), label, font=label_font)
    tw = bbox[2] - bbox[0]
    draw.text((CARD_W // 2 - tw // 2, 24), label, fill=(20, 20, 20), font=label_font)
    img.save(out, "JPEG", quality=92)


def _draw_length_bar(
    draw: ImageDraw.ImageDraw,
    x0: float,
    step: float,
    y: int,
    start: int,
    end: int,
    color: tuple[int, int, int],
    *,
    width: int = 12,
) -> None:
    xa = int(x0 + start * step)
    xb = int(x0 + end * step)
    draw.line((xa, y, xb, y), fill=color, width=width)


def _draw_numberline_lengths_separate(a: int, b: int, out: Path, *, max_n: int = 5) -> None:
    """Axis on top; two parallel bars from 0 of lengths a and b."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    axis_y = 95
    x0, _, step = _draw_numberline_axis(draw, max_n=max_n, y=axis_y, font_size=28)
    seg_y1 = 175
    seg_y2 = 245
    col_a = (45, 95, 165)
    col_b = (165, 75, 45)
    _draw_length_bar(draw, x0, step, seg_y1, 0, a, col_a)
    _draw_length_bar(draw, x0, step, seg_y2, 0, b, col_b)
    font = _font(30)
    draw.text((int(x0 + a * step) + 10, seg_y1 - 24), str(a), fill=col_a, font=font)
    draw.text((int(x0 + b * step) + 10, seg_y2 - 24), str(b), fill=col_b, font=font)
    x_origin = int(x0)
    draw.line((x_origin, axis_y - 10, x_origin, seg_y2 + 14), fill=(190, 190, 188), width=2)
    img.save(out, "JPEG", quality=92)


def _draw_numberline_length_pure(n: int, out: Path, *, max_n: int = 5) -> None:
    """One bar 0→n on axis; no «+», no second segment (S4 length-only)."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    axis_y = 100
    x0, _, step = _draw_numberline_axis(draw, max_n=max_n, y=axis_y, font_size=28)
    seg_y = 200
    col = (45, 95, 165)
    _draw_length_bar(draw, x0, step, seg_y, 0, n, col)
    for mark in (0, n):
        x = int(x0 + mark * step)
        draw.line((x, seg_y - 22, x, seg_y + 22), fill=(30, 30, 30), width=3)
    x_origin = int(x0)
    draw.line((x_origin, axis_y - 8, x_origin, seg_y + 16), fill=(190, 190, 188), width=2)
    font = _font(32)
    draw.text((int(x0 + n * step) + 12, seg_y - 18), str(n), fill=col, font=font)
    img.save(out, "JPEG", quality=92)


def _draw_numberline_add(a: int, b: int, out: Path, *, max_n: int = 5) -> None:
    """Concatenate lengths a then b from 0; label a+b."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    axis_y = 95
    x0, _, step = _draw_numberline_axis(draw, max_n=max_n, y=axis_y, font_size=28)
    seg_y = 190
    total = a + b
    col_a = (45, 95, 165)
    col_b = (165, 75, 45)
    _draw_length_bar(draw, x0, step, seg_y, 0, a, col_a)
    _draw_length_bar(draw, x0, step, seg_y, a, total, col_b)
    for n in (0, a, total):
        x = int(x0 + n * step)
        draw.line((x, seg_y - 20, x, seg_y + 20), fill=(30, 30, 30), width=3)
    label = f"{a}+{b}"
    label_font = _font(44)
    bbox = draw.textbbox((0, 0), label, font=label_font)
    tw = bbox[2] - bbox[0]
    draw.text((CARD_W // 2 - tw // 2, seg_y + 48), label, fill=(20, 20, 20), font=label_font)
    img.save(out, "JPEG", quality=92)


def _draw_numberline_sub(total: int, subtract: int, out: Path, *, max_n: int = 5) -> None:
    """Full bar 0..total; rightmost `subtract` units marked removed; label total-subtract."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    axis_y = 95
    x0, _, step = _draw_numberline_axis(draw, max_n=max_n, y=axis_y, font_size=28)
    seg_y = 190
    remain = total - subtract
    col_keep = (45, 95, 165)
    col_cut = (195, 175, 170)
    col_ghost = (210, 210, 208)
    _draw_length_bar(draw, x0, step, seg_y, 0, total, col_ghost, width=14)
    _draw_length_bar(draw, x0, step, seg_y, 0, remain, col_keep)
    _draw_length_bar(draw, x0, step, seg_y, remain, total, col_cut)
    for n in (0, remain, total):
        x = int(x0 + n * step)
        draw.line((x, seg_y - 20, x, seg_y + 20), fill=(30, 30, 30), width=3)
    label = f"{total}-{subtract}"
    label_font = _font(44)
    bbox = draw.textbbox((0, 0), label, font=label_font)
    tw = bbox[2] - bbox[0]
    draw.text((CARD_W // 2 - tw // 2, seg_y + 48), label, fill=(20, 20, 20), font=label_font)
    img.save(out, "JPEG", quality=92)


def _venn_geometry(*, disjoint: bool = False, subset: bool = False) -> dict[str, int]:
    cy = CARD_H // 2 + 10
    rx, ry = 130, 100
    if subset:
        return {
            "cx_a": CARD_W // 2,
            "cx_b": CARD_W // 2,
            "cy": cy,
            "rx_a": 55,
            "ry_a": 45,
            "rx_b": rx,
            "ry_b": ry,
            "disjoint": False,
            "subset": True,
        }
    if disjoint:
        return {
            "cx_a": CARD_W // 2 - 150,
            "cx_b": CARD_W // 2 + 150,
            "cy": cy,
            "rx_a": rx,
            "ry_a": ry,
            "rx_b": rx,
            "ry_b": ry,
            "disjoint": True,
            "subset": False,
        }
    return {
        "cx_a": CARD_W // 2 - 75,
        "cx_b": CARD_W // 2 + 75,
        "cy": cy,
        "rx_a": rx,
        "ry_a": ry,
        "rx_b": rx,
        "ry_b": ry,
        "disjoint": False,
        "subset": False,
    }


def _ellipse_mask(size: tuple[int, int], cx: int, cy: int, rx: int, ry: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=255)
    return mask


def _draw_venn_regions(
    out: Path,
    *,
    highlight: str = "none",
    disjoint: bool = False,
    subset: bool = False,
    labels: bool = True,
) -> None:
    """Euler–Venn: заливка **областей** (не счёт точек). highlight: none|disjoint|intersect|union|subset|a_only."""
    g = _venn_geometry(disjoint=disjoint, subset=subset)
    size = (CARD_W, CARD_H)
    img = _blank().convert("RGBA")
    color_a = (55, 95, 175)
    color_b = (195, 85, 65)
    fill_a = (*color_a, 110)
    fill_b = (*color_b, 110)
    fill_both = (120, 70, 140, 130)

    mask_a = _ellipse_mask(size, g["cx_a"], g["cy"], g["rx_a"], g["ry_a"])
    mask_b = _ellipse_mask(size, g["cx_b"], g["cy"], g["rx_b"], g["ry_b"])
    intersect = ImageChops.multiply(mask_a, mask_b)
    union = ImageChops.add(mask_a, mask_b)
    a_only = ImageChops.subtract(mask_a, mask_b)
    b_only = ImageChops.subtract(mask_b, mask_a)

    hl = highlight
    if hl == "disjoint":
        hl = "disjoint_ab"

    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    if hl == "intersect":
        layer.paste(Image.new("RGBA", size, fill_both), (0, 0), intersect)
    elif hl == "union" or hl == "disjoint_ab":
        layer.paste(Image.new("RGBA", size, fill_a), (0, 0), mask_a)
        layer.paste(Image.new("RGBA", size, fill_b), (0, 0), mask_b)
    elif hl == "subset":
        layer.paste(Image.new("RGBA", size, fill_a), (0, 0), mask_a)
    elif hl == "a_only":
        layer.paste(Image.new("RGBA", size, fill_a), (0, 0), a_only)
    elif hl == "b_only":
        layer.paste(Image.new("RGBA", size, fill_b), (0, 0), b_only)

    img = Image.alpha_composite(img, layer)
    draw = ImageDraw.Draw(img)
    if g["subset"]:
        draw.ellipse(
            (g["cx_b"] - g["rx_b"], g["cy"] - g["ry_b"], g["cx_b"] + g["rx_b"], g["cy"] + g["ry_b"]),
            outline=color_b,
            width=5,
        )
        draw.ellipse(
            (g["cx_a"] - g["rx_a"], g["cy"] - g["ry_a"], g["cx_a"] + g["rx_a"], g["cy"] + g["ry_a"]),
            outline=color_a,
            width=5,
        )
    else:
        draw.ellipse(
            (g["cx_a"] - g["rx_a"], g["cy"] - g["ry_a"], g["cx_a"] + g["rx_a"], g["cy"] + g["ry_a"]),
            outline=color_a,
            width=5,
        )
        draw.ellipse(
            (g["cx_b"] - g["rx_b"], g["cy"] - g["ry_b"], g["cx_b"] + g["rx_b"], g["cy"] + g["ry_b"]),
            outline=color_b,
            width=5,
        )

    if labels:
        try:
            font = ImageFont.truetype("arial.ttf", 28)
        except OSError:
            font = ImageFont.load_default()
        if g["subset"]:
            draw.text((g["cx_a"] - 8, g["cy"] - g["ry_a"] - 36), "A", fill=color_a, font=font)
            draw.text((g["cx_b"] + g["rx_b"] - 24, g["cy"] - g["ry_b"] - 36), "B", fill=color_b, font=font)
        else:
            draw.text((g["cx_a"] - g["rx_a"] + 8, g["cy"] - g["ry_a"] - 36), "A", fill=color_a, font=font)
            draw.text((g["cx_b"] + g["rx_b"] - 32, g["cy"] - g["ry_b"] - 36), "B", fill=color_b, font=font)

    img.convert("RGB").save(out, "JPEG", quality=92)


def _nline_set_interval_pair(*, variant: str) -> tuple[tuple[int, int], tuple[int, int]]:
    """Return (A0, A1), (B0, B1) on axis ticks. variant: overlap|disjoint|subset."""
    if variant == "disjoint":
        return (1, 2), (4, 5)
    if variant == "subset":
        return (2, 3), (1, 4)
    return (1, 4), (2, 5)


def _interval_text(lo: int, hi: int) -> str:
    return f"[{lo}; {hi}]"


def _x_at_tick(x0: float, step: float, tick: int) -> int:
    return int(x0 + tick * step)


def _draw_numberline_axis_arrow(
    draw: ImageDraw.ImageDraw,
    *,
    max_n: int = 6,
    y: int = 250,
    font_size: int = 30,
) -> tuple[float, int, float]:
    """Textbook-style axis with arrow; tick labels below (not covered by interval bar)."""
    x0, x1, axis_y, step = _numberline_layout(max_n=max_n, y=y)
    font = _font(font_size)
    draw.line((x0, axis_y, x1 - 18, axis_y), fill=(30, 30, 30), width=3)
    ax = x1 - 10
    draw.polygon(
        [(ax, axis_y), (ax - 14, axis_y - 7), (ax - 14, axis_y + 7)],
        fill=(30, 30, 30),
    )
    for i in range(max_n + 1):
        x = int(x0 + i * step)
        draw.line((x, axis_y - 8, x, axis_y + 8), fill=(30, 30, 30), width=2)
        draw.text((x - 8, axis_y + 14), str(i), fill=(20, 20, 20), font=font)
    return x0, axis_y, step


def _draw_endpoint_closed(
    draw: ImageDraw.ImageDraw,
    x: int,
    axis_y: int,
    *,
    r: int = 7,
    fill: tuple[int, int, int] = (25, 25, 25),
) -> None:
    draw.ellipse((x - r, axis_y - r, x + r, axis_y + r), fill=fill, outline=fill)


def _draw_textbook_interval(
    draw: ImageDraw.ImageDraw,
    x0: float,
    step: float,
    axis_y: int,
    lo: int,
    hi: int,
    *,
    color: tuple[int, int, int],
    bar_above: int = 20,
    line_width: int = 7,
    mark_endpoints: bool = True,
    endpoint_fill: tuple[int, int, int] | None = None,
) -> None:
    """Interval like school reference: thick bar above axis; optional dots at endpoints on axis."""
    xa = _x_at_tick(x0, step, lo)
    xb = _x_at_tick(x0, step, hi)
    bar_y = axis_y - bar_above
    draw.line((xa, bar_y, xb, bar_y), fill=color, width=line_width)
    if mark_endpoints:
        dot = endpoint_fill if endpoint_fill is not None else (25, 25, 25)
        _draw_endpoint_closed(draw, xa, axis_y, fill=dot)
        _draw_endpoint_closed(draw, xb, axis_y, fill=dot)


NLINE_SET_COL_A = (55, 120, 200)
NLINE_SET_COL_B = (210, 105, 70)
NLINE_SET_COL_RESULT = (128, 32, 48)  # бордовый — линия результата и подпись


def _nline_set_highlight_range(
    highlight: str,
    a: tuple[int, int],
    b: tuple[int, int],
) -> list[tuple[int, int]]:
    """Tick range lo..hi for the result interval (empty for disjoint)."""
    a0, a1 = a
    b0, b1 = b
    hl = highlight
    if hl == "intersect":
        return [(max(a0, b0), min(a1, b1))]
    if hl == "union":
        return [(min(a0, b0), max(a1, b1))]
    if hl == "subset":
        return [(a0, a1)]
    if hl == "a_only":
        if a0 < b0:
            return [(a0, min(a1, b0))]
        if a1 > b1:
            return [(max(a0, b1), a1)]
        return []
    if hl == "disjoint":
        return []
    return []


def _draw_geom_line_infinite(out: Path) -> None:
    """Прямая: линия со стрелками на обоих концах (бесконечность), без подписи на кадре."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    y = CARD_H // 2
    x0, x1 = 72, CARD_W - 72
    ink = (30, 30, 30)
    draw.line((x0 + 18, y, x1 - 18, y), fill=ink, width=5)
    draw.polygon([(x0, y), (x0 + 16, y - 8), (x0 + 16, y + 8)], fill=ink)
    draw.polygon([(x1, y), (x1 - 16, y - 8), (x1 - 16, y + 8)], fill=ink)
    img.save(out, "JPEG", quality=92)


    img.save(out, "JPEG", quality=92)


def _draw_geom_angle(
    out: Path,
    *,
    deg: float,
    right_mark: bool = False,
    vertex_label: str = "O",
) -> None:
    """Угол в вершине O: луч вдоль +x и второй луч; дуга; опционально маркер 90°."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    ink = (30, 30, 30)
    arc_col = (45, 95, 165)
    ox, oy = 300, 310
    arm = 170
    x1, y1 = ox + arm, oy
    rad = math.radians(deg)
    x2 = ox + int(arm * math.cos(rad))
    y2 = oy - int(arm * math.sin(rad))
    draw.line((ox, oy, x1, y1), fill=ink, width=7)
    draw.line((ox, oy, x2, y2), fill=ink, width=7)
    _draw_endpoint_closed(draw, ox, oy, r=7)
    arc_r = 52
    bbox = (ox - arc_r, oy - arc_r, ox + arc_r, oy + arc_r)
    draw.arc(bbox, start=0, end=int(deg), fill=arc_col, width=4)
    if right_mark:
        s = 22
        draw.line((ox + s, oy, ox + s, oy - s), fill=arc_col, width=3)
        draw.line((ox + s, oy - s, ox, oy - s), fill=arc_col, width=3)
    font = _font(36)
    draw.text((ox - 18, oy + 14), vertex_label, fill=ink, font=font)
    img.save(out, "JPEG", quality=92)


def _draw_geom_lines_parallel(out: Path) -> None:
    """Две параллельные прямые (один наклон — горизонталь), разные линии."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    ink = (30, 30, 30)
    x0, x1 = 90, CARD_W - 90
    for y in (175, 305):
        draw.line((x0, y, x1, y), fill=ink, width=6)
    img.save(out, "JPEG", quality=92)


def _draw_geom_lines_perpendicular(out: Path) -> None:
    """Перпендикулярные прямые + маркер прямого угла."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    ink = (30, 30, 30)
    mark = (45, 95, 165)
    cx, cy = 320, 250
    draw.line((80, cy, CARD_W - 80, cy), fill=ink, width=6)
    draw.line((cx, 70, cx, CARD_H - 70), fill=ink, width=6)
    s = 26
    draw.line((cx + s, cy, cx + s, cy - s), fill=mark, width=4)
    draw.line((cx + s, cy - s, cx, cy - s), fill=mark, width=4)
    img.save(out, "JPEG", quality=92)


def _draw_geom_sweep_segment(out: Path) -> None:
    """Исходный отрезок a (горизонталь внизу) — без подписи на JPEG."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    ink = (30, 30, 30)
    y = 360
    xa, xb = 180, 460
    draw.line((xa, y, xb, y), fill=ink, width=8)
    _draw_endpoint_closed(draw, xa, y, r=8)
    _draw_endpoint_closed(draw, xb, y, r=8)
    img.save(out, "JPEG", quality=92)


def _draw_geom_sweep_translate(out: Path, *, shift: int) -> None:
    """Отрезок a и копия после переноса вверх (стрелка ⊥). shift — длина переноса."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    ink = (30, 30, 30)
    arrow = (165, 75, 45)
    xa, xb = 180, 460
    y0 = 360
    y1 = y0 - shift
    for y in (y0, y1):
        draw.line((xa, y, xb, y), fill=ink, width=8)
        _draw_endpoint_closed(draw, xa, y, r=8)
        _draw_endpoint_closed(draw, xb, y, r=8)
    mx = (xa + xb) // 2
    draw.line((mx, y0 - 8, mx, y1 + 8), fill=arrow, width=4)
    draw.polygon([(mx, y1 + 4), (mx - 10, y1 + 18), (mx + 10, y1 + 18)], fill=arrow)
    img.save(out, "JPEG", quality=92)


def _draw_geom_sweep_square(out: Path, *, side: int = 200) -> None:
    """Контур квадрата после переноса a→a (⊥)."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    ink = (30, 30, 30)
    cx, cy = 320, 250
    h = side // 2
    draw.rectangle((cx - h, cy - h, cx + h, cy + h), outline=ink, width=6)
    img.save(out, "JPEG", quality=92)


def _draw_geom_sweep_rect(out: Path, *, w: int = 280, h: int = 160) -> None:
    """Контур прямоугольника a×b после переноса."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    ink = (30, 30, 30)
    cx, cy = 320, 250
    draw.rectangle((cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2), outline=ink, width=6)
    img.save(out, "JPEG", quality=92)


def _draw_geom_rectangle_width(out: Path) -> None:
    """Прямоугольник: выделена ширина (горизонтальный размер сверху)."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    ink = (30, 30, 30)
    col = (165, 75, 45)
    cx, cy = 320, 260
    w, h = 300, 170
    x0, y0 = cx - w // 2, cy - h // 2
    x1, y1 = cx + w // 2, cy + h // 2
    draw.rectangle((x0, y0, x1, y1), outline=ink, width=5)
    wy = y0 - 36
    draw.line((x0, wy, x1, wy), fill=col, width=4)
    draw.line((x0, wy, x0, y0), fill=col, width=3)
    draw.line((x1, wy, x1, y0), fill=col, width=3)
    for x, dx in ((x0, 8), (x1, -8)):
        draw.polygon([(x, wy), (x + dx, wy - 10), (x + dx, wy + 10)], fill=col)
    img.save(out, "JPEG", quality=92)


def _draw_geom_segment(out: Path) -> None:
    """Отрезок: ограниченный отрезок с точками на концах, без подписи."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    y = CARD_H // 2
    xa, xb = 150, CARD_W - 150
    ink = (30, 30, 30)
    draw.line((xa, y, xb, y), fill=ink, width=8)
    _draw_endpoint_closed(draw, xa, y, r=8)
    _draw_endpoint_closed(draw, xb, y, r=8)
    img.save(out, "JPEG", quality=92)


def _draw_two_segments_compare(out: Path, *, len_a: int, len_b: int) -> None:
    """Два отрезка A (сверху) и B (снизу), общее начало слева — compare длины."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    ink = (30, 30, 30)
    x0 = 100
    y_a, y_b = 170, 290
    label_font = _font(40)
    for y, length, label in ((y_a, len_a, "A"), (y_b, len_b, "B")):
        xa, xb = x0, x0 + length
        draw.line((xa, y, xb, y), fill=ink, width=8)
        _draw_endpoint_closed(draw, xa, y, r=8)
        _draw_endpoint_closed(draw, xb, y, r=8)
        draw.text((x0 - 40, y - 16), label, fill=ink, font=label_font)
    img.save(out, "JPEG", quality=92)


def _draw_spatial_lr_points(out: Path, *, x_a: int, x_b: int, y: int = 240) -> None:
    """A и B на одной горизонтали — левее/правее (не два ряда отрезков)."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    ink = (30, 30, 30)
    axis_y = y
    draw.line((60, axis_y, CARD_W - 60, axis_y), fill=(210, 210, 208), width=3)
    label_font = _font(40)
    r = 10
    for x, label in ((x_a, "A"), (x_b, "B")):
        draw.ellipse((x - r, axis_y - r, x + r, axis_y + r), fill=ink)
        draw.text((x - 12, axis_y - 52), label, fill=ink, font=label_font)
    img.save(out, "JPEG", quality=92)


def _draw_spatial_ab_points(out: Path, *, y_a: int, y_b: int, x: int = 320) -> None:
    """A и B на одной вертикали — выше/ниже (точки, не compare-длина)."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    ink = (30, 30, 30)
    draw.line((x, 60, x, CARD_H - 60), fill=(210, 210, 208), width=3)
    label_font = _font(40)
    r = 10
    for y, label in ((y_a, "A"), (y_b, "B")):
        draw.ellipse((x - r, y - r, x + r, y + r), fill=ink)
        draw.text((x + 24, y - 16), label, fill=ink, font=label_font)
    img.save(out, "JPEG", quality=92)


def _draw_spatial_between_points(
    out: Path,
    *,
    labels: tuple[str, str, str],
    xs: tuple[int, int, int],
    y: int = 240,
) -> None:
    """Три метки на одной горизонтали — средняя «между» крайними (A, B, C или 1, 2, 3)."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    ink = (30, 30, 30)
    axis_y = y
    x0, x1 = min(xs) - 50, max(xs) + 50
    draw.line((max(60, x0), axis_y, min(CARD_W - 60, x1), axis_y), fill=(210, 210, 208), width=3)
    label_font = _font(40)
    r = 10
    for x, label in zip(xs, labels, strict=True):
        draw.ellipse((x - r, axis_y - r, x + r, axis_y + r), fill=ink)
        bbox = draw.textbbox((0, 0), label, font=label_font)
        tw = bbox[2] - bbox[0]
        draw.text((x - tw // 2, axis_y - 52), label, fill=ink, font=label_font)
    img.save(out, "JPEG", quality=92)


def _draw_geom_stroke(out: Path) -> None:
    """Линия: чертёжный штрих без концов, без подписи."""
    img = _blank()
    draw = ImageDraw.Draw(img)
    y = CARD_H // 2
    ink = (30, 30, 30)
    draw.line((120, y, CARD_W - 120, y), fill=ink, width=6)
    img.save(out, "JPEG", quality=92)


def _nline_set_op_caption(highlight: str, ranges: list[tuple[int, int]]) -> str:
    if highlight == "disjoint":
        return "A ∩ B = ∅"
    if highlight == "intersect" and ranges:
        lo, hi = ranges[0]
        return f"A ∩ B = {_interval_text(lo, hi)}"
    if highlight == "union" and ranges:
        lo, hi = ranges[0]
        return f"A ∪ B = {_interval_text(lo, hi)}"
    if highlight == "subset":
        return "A ⊂ B"
    if highlight == "a_only" and ranges:
        lo, hi = ranges[0]
        return f"A \\ B = {_interval_text(lo, hi)}"
    return {
        "intersect": "A ∩ B",
        "union": "A ∪ B",
        "subset": "A ⊂ B",
        "a_only": "A \\ B",
    }.get(highlight, "")


def _draw_nline_set_interval(
    out: Path,
    *,
    highlight: str = "none",
    variant: str = "overlap",
    labels: bool = True,
) -> None:
    """Sets on number line — textbook style (bar above axis, dots at endpoints)."""
    (a0, a1), (b0, b1) = _nline_set_interval_pair(variant=variant)
    img = _blank()
    draw = ImageDraw.Draw(img)
    axis_y = 268
    x0, axis_y, step = _draw_numberline_axis_arrow(draw, max_n=6, y=axis_y, font_size=30)

    col_a = NLINE_SET_COL_A
    col_b = NLINE_SET_COL_B
    col_res = NLINE_SET_COL_RESULT
    title_font = _font(26)
    cap_font = _font(34, symbols=True)

    if labels:
        draw.text((36, 36), f"A = {_interval_text(a0, a1)}", fill=col_a, font=title_font)
        draw.text((36, 68), f"B = {_interval_text(b0, b1)}", fill=col_b, font=title_font)
        _draw_textbook_interval(
            draw,
            x0,
            step,
            axis_y,
            a0,
            a1,
            color=col_a,
            bar_above=58,
            line_width=5,
            mark_endpoints=False,
        )
        _draw_textbook_interval(
            draw,
            x0,
            step,
            axis_y,
            b0,
            b1,
            color=col_b,
            bar_above=42,
            line_width=5,
            mark_endpoints=False,
        )

    ranges = _nline_set_highlight_range(highlight, (a0, a1), (b0, b1))
    for lo, hi in ranges:
        _draw_textbook_interval(
            draw,
            x0,
            step,
            axis_y,
            lo,
            hi,
            color=col_res,
            bar_above=24,
            line_width=9,
            mark_endpoints=True,
            endpoint_fill=col_res,
        )

    op = _nline_set_op_caption(highlight, ranges)
    if op:
        draw.text((36, 380), op, fill=col_res, font=cap_font)

    img.save(out, "JPEG", quality=92)


def _compose_sprites(
    out: Path,
    sprite: Image.Image,
    count: int,
    *,
    size: int,
    spread: int,
) -> None:
    img = _blank()
    cx = CARD_W // 2
    cy = CARD_H // 2
    start_x = cx - (count - 1) * spread // 2
    for i in range(count):
        _paste_centered(img, sprite, (start_x + i * spread, cy), size)
    img.save(out, "JPEG", quality=92)


def main() -> None:
    assets_dir = ROOT / "_assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    sprites: dict[str, Image.Image] = {}
    for name, url in ASSETS.items():
        ext = ".png"
        raw_path = assets_dir / f"{name}{ext}"
        if not raw_path.exists():
            raw_path.write_bytes(_fetch(_commons_url(url)))
        sprites[name] = _load_raster(raw_path.read_bytes())

    lessons = {
        "lesson-01-cardinality": [
            ("count-1-dot.jpg", lambda p: _draw_dots(1, p)),
            ("count-2-dots.jpg", lambda p: _draw_dots(2, p)),
            ("count-3-dots.jpg", lambda p: _draw_dots(3, p)),
            (
                "count-2-grains.jpg",
                lambda p: _compose_sprites(p, sprites["rice_grain"], 2, size=140, spread=160),
            ),
            (
                "count-2-cows.jpg",
                lambda p: _compose_sprites(p, sprites["cow"], 2, size=200, spread=220),
            ),
        ],
        "lesson-02-shapes": [
            ("shape-circle.jpg", lambda p: _draw_shape("circle", p)),
            ("shape-square.jpg", lambda p: _draw_shape("square", p)),
            ("shape-rectangle.jpg", lambda p: _draw_shape("rectangle", p)),
            ("count-2-shapes.jpg", lambda p: _draw_shape_row(2, "circle", p)),
            ("count-3-shapes.jpg", lambda p: _draw_shape_row(3, "square", p)),
            ("count-4-shapes.jpg", lambda p: _draw_shape_row(4, "rectangle", p)),
            ("count-5-shapes.jpg", lambda p: _draw_shape_row(5, "circle", p)),
            ("count-mixed-3c-2s-2r.jpg", lambda p: _draw_mixed_shape_counts(p, show_label=False)),
            ("count-mixed-3c-2s-2r-labeled.jpg", lambda p: _draw_mixed_shape_counts(p, show_label=True)),
        ],
        "lesson-03-numberline": [
            ("numberline-0-3.jpg", _draw_numberline),
        ],
        "lesson-04-grid": [
            ("grid-square-2x2.jpg", lambda p: _draw_gridded_rect(2, 2, p)),
            ("grid-square-3x3.jpg", lambda p: _draw_gridded_rect(3, 3, p)),
            ("grid-rect-4x2.jpg", lambda p: _draw_gridded_rect(4, 2, p)),
            ("grid-rect-3x2.jpg", lambda p: _draw_gridded_rect(3, 2, p)),
        ],
        "lesson-05-numberline-mark": [
            ("numberline-mark-1.jpg", lambda p: _draw_numberline_mark(1, p)),
            ("numberline-mark-2.jpg", lambda p: _draw_numberline_mark(2, p)),
            ("numberline-mark-3.jpg", lambda p: _draw_numberline_mark(3, p)),
        ],
        "lesson-06-numberline-compare": [
            ("numberline-compare-3gt2.jpg", lambda p: _draw_numberline_compare(3, 2, "gt", p)),
            ("numberline-compare-2lt3.jpg", lambda p: _draw_numberline_compare(2, 3, "lt", p)),
        ],
        "lesson-07-numberline-add": [
            ("numberline-lengths-2-and-3.jpg", lambda p: _draw_numberline_lengths_separate(2, 3, p)),
            ("numberline-add-2plus3.jpg", lambda p: _draw_numberline_add(2, 3, p)),
        ],
        "lesson-08-numberline-sub": [
            ("numberline-lengths-5-and-2.jpg", lambda p: _draw_numberline_lengths_separate(5, 2, p)),
            ("numberline-sub-5minus2.jpg", lambda p: _draw_numberline_sub(5, 2, p)),
        ],
        "lesson-09-commutative": [
            ("numberline-add-2plus3.jpg", lambda p: _draw_numberline_add(2, 3, p)),
            ("numberline-add-3plus2.jpg", lambda p: _draw_numberline_add(3, 2, p)),
        ],
        "lesson-10-multiply": [
            ("grid-6x3.jpg", lambda p: _draw_gridded_rect(6, 3, p)),
            ("grid-multiply-6x3.jpg", lambda p: _draw_multiply(6, 3, p)),
            ("grid-multiply-3x2.jpg", lambda p: _draw_multiply(3, 2, p)),
        ],
        "lesson-11-divide": [
            ("grid-divide-6by3.jpg", lambda p: _draw_division_square(6, 3, p)),
            ("grid-divide-6by2.jpg", lambda p: _draw_division_square(6, 2, p)),
            ("grid-divide-8by4.jpg", lambda p: _draw_division_square(8, 4, p)),
        ],
        "lesson-12-fraction": [
            ("fraction-half.jpg", lambda p: _draw_fraction(1, 2, p)),
            ("fraction-third.jpg", lambda p: _draw_fraction(1, 3, p)),
            ("fraction-two-thirds.jpg", lambda p: _draw_fraction(2, 3, p)),
            ("fraction-three-quarters.jpg", lambda p: _draw_fraction(3, 4, p)),
            ("fraction-third-6strip.jpg", lambda p: _draw_fraction_vertical_strip(6, 3, p)),
        ],
        "lesson-13-sets": [
            ("venn-two-empty.jpg", lambda p: _draw_venn_regions(p, highlight="none")),
            ("venn-region-disjoint.jpg", lambda p: _draw_venn_regions(p, highlight="disjoint", disjoint=True)),
            ("venn-region-intersect.jpg", lambda p: _draw_venn_regions(p, highlight="intersect")),
            ("venn-region-union.jpg", lambda p: _draw_venn_regions(p, highlight="union")),
            ("venn-region-subset.jpg", lambda p: _draw_venn_regions(p, highlight="subset", subset=True)),
            ("venn-region-a-only.jpg", lambda p: _draw_venn_regions(p, highlight="a_only")),
        ],
        "lesson-14-sets-interval": [
            ("nline-set-intersect.jpg", lambda p: _draw_nline_set_interval(p, highlight="intersect")),
            ("nline-set-union.jpg", lambda p: _draw_nline_set_interval(p, highlight="union")),
            (
                "nline-set-subset.jpg",
                lambda p: _draw_nline_set_interval(p, highlight="subset", variant="subset"),
            ),
            (
                "nline-set-disjoint.jpg",
                lambda p: _draw_nline_set_interval(p, highlight="disjoint", variant="disjoint"),
            ),
            ("nline-set-a-only.jpg", lambda p: _draw_nline_set_interval(p, highlight="a_only")),
        ],
        "lesson-15-geometry-words": [
            ("geom-circle.jpg", _draw_geom_lex_circle),
            ("geom-square.jpg", _draw_geom_lex_square),
            ("geom-rectangle.jpg", lambda p: _draw_shape("rectangle", p)),
            ("geom-stroke.jpg", _draw_geom_stroke),
            ("geom-segment.jpg", _draw_geom_segment),
            ("geom-line.jpg", _draw_geom_line_infinite),
        ],
        "lesson-16-geom-circle-compare": [
            (
                "geom-circles-left-greater.jpg",
                lambda p: _draw_two_circles_compare(p, left_d=160, right_d=72, relation="greater"),
            ),
            (
                "geom-circles-left-less.jpg",
                lambda p: _draw_two_circles_compare(p, left_d=72, right_d=160, relation="less"),
            ),
        ],
        "lesson-17-circle-center-radius": [
            ("geom-circle-center.jpg", _draw_geom_circle_center),
            ("geom-circle-radius.jpg", _draw_geom_circle_radius),
        ],
        "lesson-18-segment-compare": [
            ("geom-segments-equal.jpg", lambda p: _draw_two_segments_compare(p, len_a=280, len_b=280)),
            ("geom-segments-a-longer.jpg", lambda p: _draw_two_segments_compare(p, len_a=320, len_b=180)),
            ("geom-segments-a-shorter.jpg", lambda p: _draw_two_segments_compare(p, len_a=180, len_b=320)),
        ],
        "lesson-19-spatial-left-right": [
            ("geom-segments-a-left.jpg", lambda p: _draw_spatial_lr_points(p, x_a=140, x_b=460)),
            ("geom-segments-a-right.jpg", lambda p: _draw_spatial_lr_points(p, x_a=460, x_b=140)),
        ],
        "lesson-20-spatial-above-below": [
            ("geom-segments-a-above.jpg", lambda p: _draw_spatial_ab_points(p, y_a=130, y_b=350)),
            ("geom-segments-a-below.jpg", lambda p: _draw_spatial_ab_points(p, y_a=350, y_b=130)),
        ],
        "lesson-21-spatial-between": [
            (
                "geom-points-b-between-ac.jpg",
                lambda p: _draw_spatial_between_points(p, labels=("A", "B", "C"), xs=(140, 320, 500)),
            ),
            (
                "numberline-2-between-1-3.jpg",
                lambda p: _draw_spatial_between_points(p, labels=("1", "2", "3"), xs=(140, 320, 500)),
            ),
        ],
        "lesson-22-numberline-length-pure": [
            ("numberline-length-pure-2.jpg", lambda p: _draw_numberline_length_pure(2, p)),
            ("numberline-length-pure-3.jpg", lambda p: _draw_numberline_length_pure(3, p)),
        ],
        "lesson-23-geom-angles": [
            ("geom-angle-generic.jpg", lambda p: _draw_geom_angle(p, deg=70)),
            ("geom-angle-right.jpg", lambda p: _draw_geom_angle(p, deg=90, right_mark=True)),
            ("geom-angle-acute.jpg", lambda p: _draw_geom_angle(p, deg=45)),
            ("geom-angle-obtuse.jpg", lambda p: _draw_geom_angle(p, deg=135)),
        ],
        "lesson-24-geom-orientation": [
            ("geom-lines-parallel.jpg", _draw_geom_lines_parallel),
            ("geom-lines-perpendicular.jpg", _draw_geom_lines_perpendicular),
        ],
        "lesson-25-geom-sweep": [
            ("geom-sweep-segment-a.jpg", _draw_geom_sweep_segment),
            ("geom-sweep-translate-a.jpg", lambda p: _draw_geom_sweep_translate(p, shift=140)),
            ("geom-sweep-square-a.jpg", lambda p: _draw_geom_sweep_square(p, side=200)),
            ("geom-sweep-rect-ab.jpg", lambda p: _draw_geom_sweep_rect(p, w=280, h=160)),
        ],
        "lesson-26-geom-measure-width": [
            ("geom-rectangle-width.jpg", _draw_geom_rectangle_width),
        ],
        "lesson-27-numberline-compare-pure": [
            (
                "numberline-compare-pure-3gt2.jpg",
                lambda p: _draw_numberline_compare_pure_gt(3, 2, p),
            ),
            (
                "numberline-compare-pure-2lt3.jpg",
                lambda p: _draw_numberline_compare_pure_lt(2, 3, p),
            ),
        ],
    }

    built: list[str] = []
    for lesson_id, items in lessons.items():
        img_dir = ROOT / lesson_id / "images"
        img_dir.mkdir(parents=True, exist_ok=True)
        for fname, fn in items:
            path = img_dir / fname
            fn(path)
            built.append(str(path.relative_to(ROOT)).replace("\\", "/"))

    print(json.dumps({"built": len(built), "files": built}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
