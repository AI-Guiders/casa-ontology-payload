#!/usr/bin/env python3
"""FPN plan-on-tick (ADR-0035): WM plan state, step advance, emergent promote."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from casa.domain.routing import (
    ROUTE_KIND_APPLICABILITY,
    ROUTE_KIND_CAPABILITY,
    Router,
)

if TYPE_CHECKING:
    from casa.prisms.control.fpn_state import WorkingMemory


@dataclass
class PlanTick:
    """One quantum: active plan step in FPN workspace."""

    goal_id: str = ""
    active_plan_id: str = ""
    plan_steps: list[str] = field(default_factory=list)
    step_index: int = 0
    step_capability: str = ""
    step_focus: str = ""

    @classmethod
    def from_wm(cls, wm: WorkingMemory | None) -> PlanTick:
        if wm is None:
            return cls()
        return cls(
            goal_id=str(getattr(wm, "goal_id", "") or ""),
            active_plan_id=str(getattr(wm, "active_plan_id", "") or ""),
            plan_steps=list(getattr(wm, "plan_steps", None) or []),
            step_index=int(getattr(wm, "step_index", 0) or 0),
            step_capability=str(getattr(wm, "step_capability", "") or ""),
            step_focus=str(getattr(wm, "step_focus", "") or ""),
        )

    def apply_to_wm(self, wm: WorkingMemory) -> None:
        wm.goal_id = self.goal_id
        wm.active_plan_id = self.active_plan_id
        wm.plan_steps = list(self.plan_steps)
        wm.step_index = self.step_index
        wm.step_capability = self.step_capability
        wm.step_focus = self.step_focus

    def capabilities_available(self) -> tuple[str, ...]:
        return tuple(s for s in self.plan_steps if s.startswith("skill."))

    def sync_step_from_plan(self) -> None:
        if not self.plan_steps:
            self.step_capability = ""
            return
        idx = max(0, min(self.step_index, len(self.plan_steps) - 1))
        self.step_index = idx
        self.step_capability = self.plan_steps[idx]

    def advance_after_verify(self) -> bool:
        """Move to next plan step after step-level verify."""
        if not self.plan_steps:
            return False
        if self.step_index + 1 >= len(self.plan_steps):
            return False
        self.step_index += 1
        self.sync_step_from_plan()
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "active_plan_id": self.active_plan_id,
            "plan_steps": list(self.plan_steps),
            "step_index": self.step_index,
            "step_capability": self.step_capability,
            "step_focus": self.step_focus,
        }


def merge_chain_into_plan(plan: PlanTick, chain: Any) -> PlanTick:
    """Apply applicability/capability resolve results into WM plan for this tick."""
    out = PlanTick(
        goal_id=plan.goal_id,
        active_plan_id=plan.active_plan_id,
        plan_steps=list(plan.plan_steps),
        step_index=plan.step_index,
        step_capability=plan.step_capability,
        step_focus=plan.step_focus,
    )
    app = getattr(chain, "applicability", None)
    if app is not None and app.target_plan and not out.active_plan_id:
        out.active_plan_id = app.target_plan
    if app is not None and app.steps and not out.plan_steps:
        out.plan_steps = list(app.steps)
    cap = getattr(chain, "capability", None)
    if cap is not None and cap.target_skill and not out.step_capability:
        out.step_capability = cap.target_skill
    out.sync_step_from_plan()
    return out


def promote_capability_route(
    state: dict,
    *,
    match: dict[str, str],
    target_skill: str,
    gate: str,
    agent_id: str = "",
    priority: int = 0,
) -> dict[str, Any]:
    route = Router.bind(state).add_emergent_route(
        route_kind=ROUTE_KIND_CAPABILITY,
        match=match,
        target_skill=target_skill,
        gate=gate,
        agent_id=agent_id,
        priority=priority,
    )
    return route.to_row()


def promote_applicability_route(
    state: dict,
    *,
    match: dict[str, str],
    target_plan: str,
    steps: list[str],
    gate: str,
    agent_id: str = "",
    priority: int = 0,
) -> dict[str, Any]:
    route = Router.bind(state).add_emergent_route(
        route_kind=ROUTE_KIND_APPLICABILITY,
        match=match,
        target_plan=target_plan,
        steps=steps,
        gate=gate,
        agent_id=agent_id,
        priority=priority,
    )
    return route.to_row()
