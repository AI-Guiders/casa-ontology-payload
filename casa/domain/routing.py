#!/usr/bin/env python3
"""Router domain service (ADR-0016 / ADR-0020 / ADR-0035)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from casa.domain.field_state import FieldState
from casa.domain.transfer_matrix import routes_from_transfer_matrix
from casa.domain.prism_ids import PRISM_LANG_RU, PRISM_MATH, PRISM_MEMORY, PRISM_VISUAL

RouteKind = Literal["knowledge", "capability", "goal", "applicability"]

ROUTE_KIND_KNOWLEDGE: RouteKind = "knowledge"
ROUTE_KIND_CAPABILITY: RouteKind = "capability"
ROUTE_KIND_GOAL: RouteKind = "goal"
ROUTE_KIND_APPLICABILITY: RouteKind = "applicability"

_ROUTE_KINDS: tuple[RouteKind, ...] = (
    ROUTE_KIND_KNOWLEDGE,
    ROUTE_KIND_CAPABILITY,
    ROUTE_KIND_GOAL,
    ROUTE_KIND_APPLICABILITY,
)


@dataclass(frozen=True, slots=True)
class RouteContext:
    route_kind: RouteKind = ROUTE_KIND_KNOWLEDGE
    modality: str = ""
    locale: str = ""
    segment: str = ""
    tier: str = ""
    store_id: str = ""
    goal_id: str = ""
    skill_id: str = ""
    surface_class: str = ""
    novel: str = ""
    capabilities_available: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RouteTarget:
    route_kind: RouteKind = ROUTE_KIND_KNOWLEDGE
    prism_id: str = ""
    lattice_hint: str | None = None
    target_skill: str = ""
    target_goal: str = ""
    target_plan: str = ""
    steps: tuple[str, ...] = ()
    route_index: int | None = None
    matched: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "route_kind": self.route_kind,
            "matched": self.matched,
            "route_index": self.route_index,
        }
        if self.prism_id:
            out["prism_id"] = self.prism_id
            out["content_prism"] = self.prism_id
        if self.lattice_hint:
            out["lattice_hint"] = self.lattice_hint
        if self.target_skill:
            out["target_skill"] = self.target_skill
        if self.target_goal:
            out["target_goal"] = self.target_goal
        if self.target_plan:
            out["target_plan"] = self.target_plan
        if self.steps:
            out["steps"] = list(self.steps)
        return out


@dataclass
class Route:
    match: dict[str, str]
    route_kind: RouteKind = ROUTE_KIND_KNOWLEDGE
    target_prism: str = ""
    lattice_hint: str | None = None
    target_skill: str = ""
    target_goal: str = ""
    target_plan: str = ""
    steps: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    priority: int = 0

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> Route:
        m = row.get("match") or {}
        kind = str(row.get("route_kind") or ROUTE_KIND_KNOWLEDGE).strip().lower()
        if kind not in _ROUTE_KINDS:
            kind = ROUTE_KIND_KNOWLEDGE
        steps_raw = row.get("steps") or []
        steps = [str(s) for s in steps_raw if s] if isinstance(steps_raw, list) else []
        prov = row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
        return cls(
            match={str(k): _norm(str(v)) for k, v in m.items() if v},
            route_kind=kind,  # type: ignore[arg-type]
            target_prism=str(row.get("target_prism") or ""),
            lattice_hint=row.get("lattice_hint"),
            target_skill=str(row.get("target_skill") or ""),
            target_goal=str(row.get("target_goal") or ""),
            target_plan=str(row.get("target_plan") or ""),
            steps=steps,
            provenance=dict(prov),
            priority=int(row.get("priority") or 0),
        )

    def to_row(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "match": dict(self.match),
            "route_kind": self.route_kind,
            "priority": self.priority,
        }
        if self.target_prism:
            row["target_prism"] = self.target_prism
        if self.lattice_hint:
            row["lattice_hint"] = self.lattice_hint
        if self.target_skill:
            row["target_skill"] = self.target_skill
        if self.target_goal:
            row["target_goal"] = self.target_goal
        if self.target_plan:
            row["target_plan"] = self.target_plan
        if self.steps:
            row["steps"] = list(self.steps)
        if self.provenance:
            row["provenance"] = dict(self.provenance)
        return row


@dataclass(frozen=True, slots=True)
class RoutingChain:
    """Vertical resolve: goal → applicability → capability → knowledge (ADR-0035)."""

    goal: RouteTarget | None
    applicability: RouteTarget | None
    capability: RouteTarget | None
    knowledge: RouteTarget

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal.to_dict() if self.goal else None,
            "applicability": self.applicability.to_dict() if self.applicability else None,
            "capability": self.capability.to_dict() if self.capability else None,
            "knowledge": self.knowledge.to_dict(),
        }


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _ctx_value(ctx: RouteContext, key: str) -> str:
    mapping = {
        "modality": ctx.modality,
        "locale": ctx.locale,
        "segment": ctx.segment,
        "tier": ctx.tier,
        "store_id": ctx.store_id,
        "goal_id": ctx.goal_id,
        "goal": ctx.goal_id,
        "skill_id": ctx.skill_id,
        "skill": ctx.skill_id,
        "surface_class": ctx.surface_class,
        "novel": ctx.novel,
    }
    return _norm(mapping.get(key, ""))


def _capabilities_match(route_match: dict[str, str], available: tuple[str, ...]) -> bool:
    want = route_match.get("capabilities_available") or route_match.get("skills_available") or ""
    if not want:
        return True
    need = {_norm(x) for x in want.replace(",", " ").split() if x.strip()}
    if not need:
        return True
    have = {_norm(x) for x in available if x}
    return need.issubset(have)


def _match_score(route_match: dict[str, str], ctx: RouteContext) -> int:
    if not route_match:
        return 0
    if not _capabilities_match(route_match, ctx.capabilities_available):
        return -1
    score = 0
    for key, want in route_match.items():
        if key in ("capabilities_available", "skills_available"):
            continue
        got = _ctx_value(ctx, key)
        if not want:
            continue
        if got != _norm(want):
            return -1
        score += 10
    return score


def _target_from_route(route: Route, index: int) -> RouteTarget:
    return RouteTarget(
        route_kind=route.route_kind,
        prism_id=route.target_prism,
        lattice_hint=route.lattice_hint,
        target_skill=route.target_skill,
        target_goal=route.target_goal,
        target_plan=route.target_plan,
        steps=tuple(route.steps),
        route_index=index,
        matched=dict(route.match),
    )


class Router:
    """Routing over prism_router block inside FieldState."""

    def __init__(self, field: FieldState) -> None:
        self._field = field
        self._prism = field.router_prism()

    @classmethod
    def bind(cls, state: dict) -> Router:
        return cls(FieldState.bind(state))

    def routes(self, *, route_kind: RouteKind | None = None) -> list[Route]:
        rows = [Route.from_row(r) for r in self._prism.routes if isinstance(r, dict)]
        if route_kind is None:
            return rows
        return [r for r in rows if r.route_kind == route_kind]

    def set_routes(self, routes: list[Route]) -> None:
        rows = [r.to_row() for r in routes]
        rows.sort(key=lambda r: int(r.get("priority") or 0), reverse=True)
        self._prism.block["routes"] = rows

    def add_route(
        self,
        match: dict[str, str],
        target_prism: str = "",
        *,
        route_kind: RouteKind = ROUTE_KIND_KNOWLEDGE,
        lattice_hint: str | None = None,
        target_skill: str = "",
        target_goal: str = "",
        target_plan: str = "",
        steps: list[str] | None = None,
        provenance: dict[str, Any] | None = None,
        priority: int = 0,
    ) -> Route:
        prism_id = ""
        if target_prism:
            from casa.prisms.memory.prism_spawn import validate_content_prism_id

            prism_id = validate_content_prism_id(target_prism)
        route = Route(
            match={k: _norm(v) for k, v in match.items() if v},
            route_kind=route_kind,
            target_prism=prism_id,
            lattice_hint=lattice_hint,
            target_skill=_norm(target_skill) if target_skill else "",
            target_goal=_norm(target_goal) if target_goal else "",
            target_plan=_norm(target_plan) if target_plan else "",
            steps=list(steps or []),
            provenance=dict(provenance or {}),
            priority=int(priority),
        )
        rows = self._prism.routes + [route.to_row()]
        self._prism.block["routes"] = rows
        self._prism.block["routes"].sort(key=lambda r: int(r.get("priority") or 0), reverse=True)
        self._field.bump_field_version()
        return route

    def remove_route(
        self,
        match: dict[str, str],
        *,
        route_kind: RouteKind,
    ) -> bool:
        """Drop route with exact normalized match (Kolb supersede)."""
        norm_match = {_norm(k): _norm(v) for k, v in match.items() if v}
        rows = self._prism.routes
        kept = [
            r
            for r in rows
            if not (
                isinstance(r, dict)
                and str(r.get("route_kind") or ROUTE_KIND_KNOWLEDGE) == route_kind
                and {_norm(k): _norm(v) for k, v in (r.get("match") or {}).items() if v} == norm_match
            )
        ]
        if len(kept) == len(rows):
            return False
        self._prism.block["routes"] = kept
        self._field.bump_field_version()
        return True

    def supersede_emergent_route(
        self,
        *,
        route_kind: RouteKind,
        match: dict[str, str],
        gate: str,
        agent_id: str = "",
        target_prism: str = "",
        lattice_hint: str | None = None,
        target_skill: str = "",
        target_goal: str = "",
        target_plan: str = "",
        steps: list[str] | None = None,
        priority: int = 0,
    ) -> Route:
        """Replace emergent route after Kolb verify (remove old match → add new)."""
        self.remove_route(match, route_kind=route_kind)
        return self.add_emergent_route(
            route_kind=route_kind,
            match=match,
            gate=gate,
            agent_id=agent_id,
            priority=priority,
            target_prism=target_prism,
            lattice_hint=lattice_hint,
            target_skill=target_skill,
            target_goal=target_goal,
            target_plan=target_plan,
            steps=steps,
            extra_provenance={"supersedes": True},
        )

    def add_emergent_route(
        self,
        *,
        route_kind: RouteKind,
        match: dict[str, str],
        gate: str,
        agent_id: str = "",
        priority: int = 0,
        target_prism: str = "",
        lattice_hint: str | None = None,
        target_skill: str = "",
        target_goal: str = "",
        target_plan: str = "",
        steps: list[str] | None = None,
        extra_provenance: dict[str, Any] | None = None,
    ) -> Route:
        """Promote route after verify gate (ADR-0035); not design-time seed."""
        prov: dict[str, Any] = {"gate": gate, "emergent": True}
        if agent_id:
            prov["agent_id"] = agent_id
        if extra_provenance:
            prov.update(extra_provenance)
        return self.add_route(
            match,
            target_prism,
            route_kind=route_kind,
            lattice_hint=lattice_hint,
            target_skill=target_skill,
            target_goal=target_goal,
            target_plan=target_plan,
            steps=steps,
            provenance=prov,
            priority=priority,
        )

    def _content_prism_has_lattices(self, prism_id: str) -> bool:
        from casa.domain.prism_wire import prism_memory, prisms

        block = prisms(self._field.wire).get(prism_id)
        if not isinstance(block, dict):
            return False
        if block.get("lattices"):
            return True
        if prism_id == PRISM_MEMORY:
            mem = prism_memory(self._field.wire).get("lattices") or {}
            legacy = (self._field.wire.get("sss") or {}).get("lattices") or {}
            return bool(mem or legacy)
        return False

    def resolve_layer(self, ctx: RouteContext) -> RouteTarget | None:
        best: RouteTarget | None = None
        best_score = -1
        for i, route in enumerate(self.routes(route_kind=ctx.route_kind)):
            sc = _match_score(route.match, ctx)
            if sc > best_score:
                best_score = sc
                best = _target_from_route(route, i)
        if best is not None and best_score >= 0:
            return best
        return None

    def resolve(self, ctx: RouteContext) -> RouteTarget:
        if ctx.route_kind != ROUTE_KIND_KNOWLEDGE:
            layer = self.resolve_layer(ctx)
            if layer is not None:
                return layer
            return RouteTarget(route_kind=ctx.route_kind, matched={"source": "unresolved"})

        best = self.resolve_layer(ctx)
        if best is not None and best.prism_id:
            if not self._content_prism_has_lattices(best.prism_id):
                fb = self._field.profile_default_content_prism() or PRISM_MEMORY
                matched = dict(best.matched or {})
                matched["logical_prism"] = best.prism_id
                matched["fallback"] = fb
                return RouteTarget(
                    route_kind=ROUTE_KIND_KNOWLEDGE,
                    prism_id=fb,
                    lattice_hint=best.lattice_hint,
                    route_index=best.route_index,
                    matched=matched,
                )
            return best
        profile_default = self._field.profile_default_content_prism()
        if profile_default:
            return RouteTarget(
                route_kind=ROUTE_KIND_KNOWLEDGE,
                prism_id=profile_default,
                lattice_hint=None,
                route_index=None,
                matched={"source": "profile"},
            )
        default = self._prism.default_content_prism
        return RouteTarget(
            route_kind=ROUTE_KIND_KNOWLEDGE,
            prism_id=default,
            lattice_hint=None,
            route_index=None,
            matched=None,
        )

    def resolve_chain(
        self,
        base: RouteContext,
        *,
        goal_id: str = "",
        skill_id: str = "",
        capabilities_available: tuple[str, ...] = (),
    ) -> RoutingChain:
        """Thalamus → goal → applicability → capability → knowledge (ADR-0035)."""
        gid = _norm(goal_id or base.goal_id)
        sid = _norm(skill_id or base.skill_id)
        caps = capabilities_available or base.capabilities_available

        goal_tgt = None
        if gid:
            goal_tgt = self.resolve_layer(
                RouteContext(
                    route_kind=ROUTE_KIND_GOAL,
                    goal_id=gid,
                    locale=base.locale,
                    modality=base.modality,
                )
            )

        app_tgt = None
        if gid:
            app_tgt = self.resolve_layer(
                RouteContext(
                    route_kind=ROUTE_KIND_APPLICABILITY,
                    goal_id=gid,
                    locale=base.locale,
                    modality=base.modality,
                    capabilities_available=caps,
                )
            )

        cap_sid = sid
        if not cap_sid and app_tgt and app_tgt.steps:
            cap_sid = _norm(app_tgt.steps[0])
        cap_tgt = None
        if cap_sid:
            cap_tgt = self.resolve_layer(
                RouteContext(
                    route_kind=ROUTE_KIND_CAPABILITY,
                    skill_id=cap_sid,
                    modality=base.modality,
                    locale=base.locale,
                    surface_class=base.surface_class,
                    novel=base.novel,
                )
            )

        know_ctx = RouteContext(
            route_kind=ROUTE_KIND_KNOWLEDGE,
            modality=base.modality,
            locale=base.locale,
            segment=base.segment,
            tier=base.tier,
            store_id=base.store_id,
        )
        knowledge_tgt = self.resolve(know_ctx)
        return RoutingChain(
            goal=goal_tgt,
            applicability=app_tgt,
            capability=cap_tgt,
            knowledge=knowledge_tgt,
        )

    def bootstrap_defaults(self, *, locale: str = "ru", force: bool = False) -> list[Route]:
        if self._prism.routes and not force:
            return self.routes()
        defaults = routes_from_transfer_matrix(locale=locale)
        if not defaults:
            loc = _norm(locale)
            defaults = [
                Route(
                    match={"modality": "schema"},
                    route_kind=ROUTE_KIND_KNOWLEDGE,
                    target_prism=PRISM_MATH,
                    lattice_hint="schema-math",
                    priority=100,
                ),
                Route(
                    match={"modality": "vis"},
                    route_kind=ROUTE_KIND_KNOWLEDGE,
                    target_prism=PRISM_VISUAL,
                    lattice_hint="V1_object",
                    priority=95,
                ),
                Route(
                    match={"modality": "t9", "locale": loc},
                    route_kind=ROUTE_KIND_KNOWLEDGE,
                    target_prism=PRISM_LANG_RU,
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
        route_kind: RouteKind = ROUTE_KIND_KNOWLEDGE,
        goal_id: str = "",
        skill_id: str = "",
        surface_class: str = "",
        novel: str = "",
        capabilities_available: tuple[str, ...] = (),
    ) -> RouteContext:
        store = field.wire.get("store") if isinstance(field.wire.get("store"), dict) else {}
        loc = field.store_locale() if locale is None else locale
        return RouteContext(
            route_kind=route_kind,
            modality=_norm(modality),
            locale=_norm(loc),
            segment=_norm(segment),
            tier=_norm(str(store.get("tier") or "")),
            store_id=_norm(str(store.get("store_id") or "")),
            goal_id=_norm(goal_id),
            skill_id=_norm(skill_id),
            surface_class=_norm(surface_class),
            novel=_norm(novel),
            capabilities_available=capabilities_available,
        )
