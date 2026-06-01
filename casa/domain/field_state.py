#!/usr/bin/env python3
"""FieldState aggregate root (ADR-0020)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from casa.domain.prism import PRISM_KIND_ROUTER, Prism, PrismCatalog, prism_from_block
from casa.prisms.shared.prism_state import PRISM_ROUTER, normalize_prisms


@dataclass
class SessionFocus:
    active_prism: str = "prism_memory"
    active_control_prism: str = "prism_control"
    active_lattice: str | None = None
    mode: str = ""
    route_lattice_hint: str | None = None
    route_matched: dict[str, str] | None = None

    @classmethod
    def from_sn(cls, sn: dict[str, Any] | None) -> SessionFocus:
        sn = sn or {}
        matched = sn.get("route_matched")
        return cls(
            active_prism=str(sn.get("active_prism") or "prism_memory"),
            active_control_prism=str(sn.get("active_control_prism") or "prism_control"),
            active_lattice=sn.get("active_lattice"),
            mode=str(sn.get("mode") or ""),
            route_lattice_hint=sn.get("route_lattice_hint"),
            route_matched=dict(matched) if isinstance(matched, dict) else None,
        )

    def apply_to_sn(self, sn: dict[str, Any]) -> None:
        sn["active_prism"] = self.active_prism
        sn["active_control_prism"] = self.active_control_prism
        if self.active_lattice is not None:
            sn["active_lattice"] = self.active_lattice
        if self.mode:
            sn["mode"] = self.mode
        if self.route_lattice_hint is not None:
            sn["route_lattice_hint"] = self.route_lattice_hint
        if self.route_matched is not None:
            sn["route_matched"] = self.route_matched


@dataclass
class FieldState:
    """Wrapper over wire dict; mutations write through to checkpoint JSON shape."""

    wire: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def bind(cls, state: dict[str, Any]) -> FieldState:
        normalize_prisms(state)
        return cls(wire=state)

    @property
    def field_version(self) -> int:
        return int(self.wire.get("field_version") or 0)

    def bump_field_version(self) -> None:
        self.wire["field_version"] = self.field_version + 1

    @property
    def focus(self) -> SessionFocus:
        sn = self.wire.setdefault("sn", {})
        return SessionFocus.from_sn(sn)

    def apply_focus(self, focus: SessionFocus) -> None:
        focus.apply_to_sn(self.wire.setdefault("sn", {}))

    @property
    def catalog(self) -> PrismCatalog:
        root = self.wire.setdefault("prisms", {})
        out: dict[str, Prism] = {}
        for pid, block in root.items():
            if isinstance(block, dict):
                out[str(pid)] = prism_from_block(str(pid), block)
        return PrismCatalog(prisms=out)

    def router_prism(self) -> Prism:
        block = self.wire.setdefault("prisms", {}).setdefault(
            PRISM_ROUTER,
            {
                "kind": PRISM_KIND_ROUTER,
                "schema_version": 1,
                "stack": "design/prisms/router/stack.json",
                "default_content_prism": "prism_memory",
                "routes": [],
            },
        )
        return prism_from_block(PRISM_ROUTER, block)

    def profile_default_content_prism(self) -> str | None:
        from casa.prisms.memory.prism_spawn import validate_content_prism_id

        for key in ("store", "profile"):
            block = self.wire.get(key)
            if not isinstance(block, dict):
                continue
            raw = block.get("default_content_prism")
            if raw:
                return validate_content_prism_id(str(raw))
        return None

    def store_locale(self) -> str:
        store = self.wire.get("store") if isinstance(self.wire.get("store"), dict) else {}
        return str(store.get("locale") or "ru")
