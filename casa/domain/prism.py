#!/usr/bin/env python3
"""Prism hierarchy (content / hot / router / control)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from casa.domain.lattice import Lattice

PRISM_KIND_CONTENT = "content"
PRISM_KIND_HOT_CONTEXT = "hot_context"
PRISM_KIND_ROUTER = "router"
PRISM_KIND_CONTROL = "control"


@dataclass
class Prism:
    prism_id: str
    kind: str
    stack: str = ""
    subsystem: str = ""
    block: dict[str, Any] = field(default_factory=dict)

    @property
    def supports_lattices(self) -> bool:
        return self.kind in (PRISM_KIND_CONTENT, PRISM_KIND_CONTROL)

    def lattices(self) -> dict[str, Lattice]:
        raw = self.block.get("lattices") if isinstance(self.block.get("lattices"), dict) else {}
        return {lid: Lattice.from_dict(lid, lat) for lid, lat in raw.items() if isinstance(lat, dict)}

    def set_lattices(self, lattices: dict[str, Lattice]) -> None:
        self.block["lattices"] = {lid: lat.to_dict() for lid, lat in lattices.items()}

    @property
    def routes(self) -> list[dict[str, Any]]:
        return list(self.block.get("routes") or [])

    @property
    def edges(self) -> list[dict[str, Any]]:
        return list(self.block.get("edges") or [])

    @property
    def default_content_prism(self) -> str:
        return str(self.block.get("default_content_prism") or "prism_memory")


@dataclass
class PrismCatalog:
    prisms: dict[str, Prism] = field(default_factory=dict)

    def get(self, prism_id: str) -> Prism | None:
        return self.prisms.get(prism_id)

    def require(self, prism_id: str) -> Prism:
        p = self.get(prism_id)
        if p is None:
            raise KeyError(prism_id)
        return p


def prism_from_block(prism_id: str, block: dict[str, Any]) -> Prism:
    kind = str(block.get("kind") or "")
    if not kind:
        if prism_id.endswith("_hippo") or prism_id == "prism_hippo":
            kind = "hippo"
        elif prism_id == "prism_control":
            kind = PRISM_KIND_CONTROL
        elif prism_id in ("prism_hot_context",):
            kind = PRISM_KIND_HOT_CONTEXT
        elif prism_id in ("prism_router",):
            kind = PRISM_KIND_ROUTER
        else:
            kind = PRISM_KIND_CONTENT
    return Prism(
        prism_id=prism_id,
        kind=kind,
        stack=str(block.get("stack") or ""),
        subsystem=str(block.get("subsystem") or ""),
        block=block,
    )


PrismKind = str
