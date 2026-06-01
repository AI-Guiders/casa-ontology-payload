#!/usr/bin/env python3
"""Router domain service (ADR-0016 / ADR-0020)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from casa.domain.field_state import FieldState
from casa.prisms.shared.prism_state import PRISM_MEMORY, PRISM_VISUAL


@dataclass(frozen=True, slots=True)
class RouteContext:
    modality: str = ""
    locale: str = ""
    segment: str = ""
    tier: str = ""
    store_id: str = ""


@dataclass(frozen=True, slots=True)
class RouteTarget:
    prism_id: str
    lattice_hint: str | None = None
    route_index: int | None = None
    matched: dict[str, str] | None = None


@dataclass
class Route:
    match: dict[str, str]
    target_prism: str
    lattice_hint: str | None = None
    priority: int = 0

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> Route:
        m = row.get("match") or {}
        return cls(
            match={str(k): _norm(str(v)) for k, v in m.items() if v},
            target_prism=str(row.get("target_prism") or PRISM_MEMORY),
            lattice_hint=row.get("lattice_hint"),
            priority=int(row.get("priority") or 0),
        )

    def to_row(self) -> dict[str, Any]:
        return {
            "match": dict(self.match),
            "target_prism": self.target_prism,
            "lattice_hint": self.lattice_hint,
            "priority": self.priority,
        }


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _match_score(route_match: dict[str, str], ctx: RouteContext) -> int:
    ctx_map = {
        "modality": _norm(ctx.modality),
        "locale": _norm(ctx.locale),
        "segment": _norm(ctx.segment),
        "tier": _norm(ctx.tier),
        "store_id": _norm(ctx.store_id),
    }
    if not route_match:
        return 0
    score = 0
    for key, want in route_match.items():
        got = ctx_map.get(key, "")
        if not want:
            continue
        if got != want:
            return -1
        score += 10
    return score


class Router:
    """Routing over prism_router block inside FieldState."""

    def __init__(self, field: FieldState) -> None:
        self._field = field
        self._prism = field.router_prism()

    @classmethod
    def bind(cls, state: dict) -> Router:
        return cls(FieldState.bind(state))

    def routes(self) -> list[Route]:
        return [Route.from_row(r) for r in self._prism.routes if isinstance(r, dict)]

    def set_routes(self, routes: list[Route]) -> None:
        rows = [r.to_row() for r in routes]
        rows.sort(key=lambda r: int(r.get("priority") or 0), reverse=True)
        self._prism.block["routes"] = rows

    def add_route(
        self,
        match: dict[str, str],
        target_prism: str,
        *,
        lattice_hint: str | None = None,
        priority: int = 0,
    ) -> Route:
        from casa.prisms.memory.prism_spawn import validate_content_prism_id

        route = Route(
            match={k: _norm(v) for k, v in match.items() if v},
            target_prism=validate_content_prism_id(target_prism),
            lattice_hint=lattice_hint,
            priority=int(priority),
        )
        rows = self._prism.routes + [route.to_row()]
        self._prism.block["routes"] = rows
        self._prism.block["routes"].sort(key=lambda r: int(r.get("priority") or 0), reverse=True)
        self._field.bump_field_version()
        return route

    def resolve(self, ctx: RouteContext) -> RouteTarget:
        best: RouteTarget | None = None
        best_score = -1
        for i, route in enumerate(self.routes()):
            sc = _match_score(route.match, ctx)
            if sc > best_score:
                best_score = sc
                best = RouteTarget(
                    prism_id=route.target_prism,
                    lattice_hint=route.lattice_hint,
                    route_index=i,
                    matched=dict(route.match),
                )
        if best is not None and best_score >= 0:
            return best
        profile_default = self._field.profile_default_content_prism()
        if profile_default:
            return RouteTarget(
                prism_id=profile_default,
                lattice_hint=None,
                route_index=None,
                matched={"source": "profile"},
            )
        default = self._prism.default_content_prism
        return RouteTarget(prism_id=default, lattice_hint=None, route_index=None, matched=None)

    def bootstrap_defaults(self, *, locale: str = "ru", force: bool = False) -> list[Route]:
        if self._prism.routes and not force:
            return self.routes()
        loc = _norm(locale)
        defaults = [
            Route(
                match={"modality": "schema"},
                target_prism=PRISM_MEMORY,
                lattice_hint="schema-math",
                priority=100,
            ),
            Route(
                match={"modality": "vis"},
                target_prism=PRISM_VISUAL,
                lattice_hint="V1_object",
                priority=95,
            ),
            Route(
                match={"modality": "image"},
                target_prism=PRISM_VISUAL,
                lattice_hint="V1_object",
                priority=95,
            ),
            Route(
                match={"modality": "t9", "locale": loc},
                target_prism=PRISM_MEMORY,
                lattice_hint="L2_word",
                priority=50,
            ),
        ]
        self.set_routes(defaults)
        return defaults

    @staticmethod
    def context_from_field(
        field: FieldState,
        *,
        modality: str = "",
        segment: str = "",
        locale: str | None = None,
    ) -> RouteContext:
        store = field.wire.get("store") if isinstance(field.wire.get("store"), dict) else {}
        loc = field.store_locale() if locale is None else locale
        return RouteContext(
            modality=_norm(modality),
            locale=_norm(loc),
            segment=_norm(segment),
            tier=_norm(str(store.get("tier") or "")),
            store_id=_norm(str(store.get("store_id") or "")),
        )
