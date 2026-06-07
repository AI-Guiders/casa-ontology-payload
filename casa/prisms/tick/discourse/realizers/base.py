#!/usr/bin/env python3
"""Block realizer protocol and registry."""

from __future__ import annotations

from typing import Any, Protocol

from casa.prisms.tick.discourse.model import ClauseSketch, DiscourseContext


class BlockRealizer(Protocol):
    def matches(self, block: dict[str, Any]) -> bool: ...

    def realize(self, block: dict[str, Any], ctx: DiscourseContext) -> list[ClauseSketch]: ...


class BlockRealizerRegistry:
    def __init__(self, realizers: list[BlockRealizer]) -> None:
        self._realizers = list(realizers)

    def realize(self, block: dict[str, Any], ctx: DiscourseContext) -> list[ClauseSketch]:
        for r in self._realizers:
            if r.matches(block):
                return r.realize(block, ctx)
        return []
