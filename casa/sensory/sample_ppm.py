#!/usr/bin/env python3
"""Synthetic room-like PPM for lab / tests (no Pillow required)."""

from __future__ import annotations

from pathlib import Path


def write_synthetic_room_ppm(path: Path, *, width: int = 160, height: int = 120) -> None:
    """Gradient walls + colored blocks — rough indoor layout."""
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[bytes] = []
    for y in range(height):
        for x in range(width):
            # ceiling brighter, floor darker
            base = 40 + (y * 80 // max(1, height))
            # left wall warm, right cool
            r = min(255, base + (width - x) // 4)
            g = min(255, base + 20)
            b = min(255, base + x // 5)
            # window patch (bright blue)
            if width // 4 < x < width // 2 and height // 5 < y < height * 2 // 5:
                r, g, b = 180, 200, 240
            # sofa block (brown)
            if width // 3 < x < width * 2 // 3 and height * 3 // 5 < y < height * 9 // 10:
                r, g, b = 90, 60, 45
            rows.append(bytes((r, g, b)))
    header = f"P6\n{width} {height}\n255\n".encode("ascii")
    path.write_bytes(header + b"".join(rows))
