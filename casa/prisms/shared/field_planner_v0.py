#!/usr/bin/env python3
"""Spatial planner v0: schedule tiles for windowed NCA train and repair."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import random
from dataclasses import dataclass, field

import torch

from casa.prisms.shared.field_window import Tile, tile_density, tiles_over_rect
from casa.prisms.shared.layout_apply import Rect


@dataclass
class FieldPlannerV0:
    """
    Heuristic tile scheduler.

    Train: density-weighted random tiles (more updates where the bundle is active).
    Repair: deterministic order — dense tiles first.
    """

    tiles: list[Tile]
    densities: list[float] = field(default_factory=list)
    _total_density: float = 0.0

    @classmethod
    def from_field_tensor(
        cls,
        tgt: torch.Tensor,
        rect: Rect,
        *,
        tile_w: int,
        tile_h: int,
        stride_x: int,
        stride_y: int,
        min_density: float = 1e-6,
    ) -> FieldPlannerV0:
        tiles = tiles_over_rect(rect, tile_w=tile_w, tile_h=tile_h, stride_x=stride_x, stride_y=stride_y)
        densities = [max(tile_density(tgt, t), min_density) for t in tiles]
        total = sum(densities)
        return cls(tiles=tiles, densities=densities, _total_density=total)

    @classmethod
    def from_bundles_union(
        cls,
        tensors: list[torch.Tensor],
        rect: Rect,
        *,
        tile_w: int,
        tile_h: int,
        stride_x: int,
        stride_y: int,
    ) -> FieldPlannerV0:
        """Union density = max activation across bundle targets."""
        tiles = tiles_over_rect(rect, tile_w=tile_w, tile_h=tile_h, stride_x=stride_x, stride_y=stride_y)
        densities: list[float] = []
        for t in tiles:
            d = 0.0
            for tgt in tensors:
                d = max(d, tile_density(tgt, t))
            densities.append(max(d, 1e-6))
        return cls(tiles=tiles, densities=densities, _total_density=sum(densities))

    def sample_train_tiles(self, n: int, *, epoch: int, seed: int) -> list[Tile]:
        if not self.tiles:
            return []
        rng = random.Random(seed + epoch * 10007)
        weights = self.densities
        return [rng.choices(self.tiles, weights=weights, k=1)[0] for _ in range(n)]

    def repair_order(self) -> list[Tile]:
        order = sorted(
            range(len(self.tiles)),
            key=lambda i: (-self.densities[i], self.tiles[i].y0, self.tiles[i].x0),
        )
        return [self.tiles[i] for i in order]

    def summary(self) -> dict:
        return {
            "tile_count": len(self.tiles),
            "total_density": self._total_density,
            "max_density": max(self.densities) if self.densities else 0.0,
            "min_density": min(self.densities) if self.densities else 0.0,
        }
