#!/usr/bin/env python3
"""Raw RGB frame from periphery (value object)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RgbFrame:
    width: int
    height: int
    rgb: bytes  # row-major R,G,B per pixel

    def __post_init__(self) -> None:
        n = int(self.width) * int(self.height) * 3
        if len(self.rgb) != n:
            raise ValueError(f"rgb length {len(self.rgb)} != {n} for {self.width}x{self.height}")

    def pixel(self, x: int, y: int) -> tuple[int, int, int]:
        i = (y * self.width + x) * 3
        return self.rgb[i], self.rgb[i + 1], self.rgb[i + 2]
