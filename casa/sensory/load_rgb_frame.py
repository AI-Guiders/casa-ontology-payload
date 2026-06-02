#!/usr/bin/env python3
"""Load RgbFrame from image files (camera export / lab)."""

from __future__ import annotations

from pathlib import Path

from casa.sensory.rgb_frame import RgbFrame


def _load_ppm(path: Path) -> RgbFrame:
    lines: list[bytes] = []
    with path.open("rb") as f:
        header = f.readline()
        if header.strip() != b"P6":
            raise ValueError(f"expected PPM P6, got {header!r}")
        while True:
            line = f.readline()
            if not line or line.startswith(b"#"):
                continue
            lines.append(line)
            if len(lines) == 2:
                break
        w, h = (int(x) for x in lines[0].split())
        maxval = int(lines[1].split()[0])
        if maxval > 255:
            raise ValueError(f"PPM maxval {maxval} not supported")
        data = f.read()
    if len(data) != w * h * 3:
        raise ValueError("PPM pixel data size mismatch")
    return RgbFrame(width=w, height=h, rgb=data)


def _load_via_pillow(path: Path) -> RgbFrame:
    from PIL import Image

    im = Image.open(path).convert("RGB")
    w, h = im.size
    return RgbFrame(width=w, height=h, rgb=im.tobytes())


def load_rgb_frame(path: Path | str) -> RgbFrame:
    p = Path(path).resolve()
    if not p.is_file():
        raise FileNotFoundError(p)
    if p.suffix.lower() in (".ppm", ".pnm"):
        return _load_ppm(p)
    try:
        return _load_via_pillow(p)
    except ImportError as e:
        raise ImportError(
            "JPEG/PNG require Pillow (pip install pillow) or convert to PPM P6"
        ) from e
