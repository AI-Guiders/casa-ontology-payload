#!/usr/bin/env python3
"""Probe gate + emergent routes (ADR-0034 / ADR-0035).

Lab probes: record gate pass → mastery journal only (`record_probe_gate`).
Routes on field: agent on macro tick (`maybe_promote_skill_on_verify`).

Tests / explicit tooling: `promote_routes_from_probe_report` after mastery streak.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from casa.domain.plan_tick import PlanTick, promote_applicability_route, promote_capability_route
from casa.domain.routing import (
    ROUTE_KIND_APPLICABILITY,
    ROUTE_KIND_CAPABILITY,
    ROUTE_KIND_GOAL,
    RouteContext,
    Router,
    _norm,
)

# Lab auto-promote: frozen v0 bootstrap only — do not add curriculum stages here.
_BOOTSTRAP_PROBES = frozenset(
    {
        "literacy-corpus-quiz",
        "analytic-read-corpus-r1",
        "phrase-compose-pilot",
        "phrase-agent-store",
    }
)


@dataclass(frozen=True, slots=True)
class TrialPlan:
    """Agent hypothesis in WM — not in router until gate pass."""

    plan_id: str
    steps: tuple[str, ...]
    goal_id: str = ""


@dataclass
class PromoteResult:
    promoted: list[dict[str, Any]] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    gate: str = ""
    passed: bool = False


def agent_id_from_state(state: dict) -> str:
    store = state.get("store") if isinstance(state.get("store"), dict) else {}
    return str(store.get("store_id") or store.get("agent_id") or "agent")


def capabilities_on_field(state: dict) -> tuple[str, ...]:
    router = Router.bind(state)
    out: list[str] = []
    for route in router.routes(route_kind=ROUTE_KIND_CAPABILITY):
        sk = (route.target_skill or "").strip()
        if sk and sk not in out:
            out.append(sk)
    return tuple(out)


def _route_already_exists(state: dict, route_kind: str, match: dict[str, str]) -> bool:
    router = Router.bind(state)
    norm_match = {_norm(k): _norm(v) for k, v in match.items() if v}
    for route in router.routes(route_kind=route_kind):  # type: ignore[arg-type]
        if route.match == norm_match:
            return True
    return False


def _safe_promote_capability(
    state: dict,
    *,
    match: dict[str, str],
    target_skill: str,
    gate: str,
    agent_id: str,
) -> dict[str, Any] | None:
    if _route_already_exists(state, ROUTE_KIND_CAPABILITY, match):
        return None
    return promote_capability_route(
        state,
        match=match,
        target_skill=target_skill,
        gate=gate,
        agent_id=agent_id,
    )


def _safe_promote_applicability(
    state: dict,
    *,
    match: dict[str, str],
    target_plan: str,
    steps: list[str],
    gate: str,
    agent_id: str,
) -> dict[str, Any] | None:
    if _route_already_exists(state, ROUTE_KIND_APPLICABILITY, match):
        return None
    return promote_applicability_route(
        state,
        match=match,
        target_plan=target_plan,
        steps=steps,
        gate=gate,
        agent_id=agent_id,
    )


def promote_goal_route(
    state: dict,
    *,
    match: dict[str, str],
    target_goal: str,
    gate: str,
    agent_id: str = "",
) -> dict[str, Any] | None:
    if _route_already_exists(state, ROUTE_KIND_GOAL, match):
        return None
    aid = agent_id or agent_id_from_state(state)
    return Router.bind(state).add_emergent_route(
        route_kind=ROUTE_KIND_GOAL,
        match=match,
        target_goal=target_goal,
        gate=gate,
        agent_id=aid,
    ).to_row()


def suggest_trial_plan(goal_id: str, capabilities: tuple[str, ...]) -> TrialPlan | None:
    """Agent-side decomposition trial (WM only until promote)."""
    gid = _norm(goal_id)
    caps = {_norm(c) for c in capabilities}

    if gid in ("goal.read.phrase", "goal.read.phrase.ru") or gid.startswith("goal.read.phrase"):
        if "skill.read.analytic" not in caps:
            return None
        steps = ["skill.read.analytic", "skill.compose.slots", "skill.verify.phrase"]
        return TrialPlan(plan_id="plan.trial.phrase_compose", steps=tuple(steps), goal_id=gid)

    if gid in ("goal.read.word", "goal.read.word.novel") or "novel" in gid:
        steps = ["skill.read.analytic", "skill.verify.lex"]
        return TrialPlan(plan_id="plan.trial.analytic_read", steps=steps, goal_id=gid)

    if gid in ("goal.learn.corpus", "goal.read.corpus") or "corpus" in gid:
        steps = ["skill.read.whole", "skill.verify.corpus"]
        return TrialPlan(plan_id="plan.trial.whole_word", steps=steps, goal_id=gid)

    if gid.startswith("goal.") and caps:
        return TrialPlan(plan_id=f"plan.trial.{gid.replace('.', '_')}", steps=tuple(sorted(caps)[:4]), goal_id=gid)

    return None


def fill_trial_plan_if_needed(state: dict, plan: PlanTick) -> PlanTick:
    """When no router applicability and no WM steps — agent trial hypothesis."""
    if plan.plan_steps or not plan.goal_id:
        return plan
    router = Router.bind(state)
    app = router.resolve_layer(
        RouteContext(route_kind=ROUTE_KIND_APPLICABILITY, goal_id=plan.goal_id, locale="ru")
    )
    if app is not None and app.steps:
        return plan
    trial = suggest_trial_plan(plan.goal_id, capabilities_on_field(state))
    if trial is None:
        return plan
    out = PlanTick(
        goal_id=plan.goal_id or trial.goal_id,
        active_plan_id=plan.active_plan_id or trial.plan_id,
        plan_steps=list(trial.steps),
        step_index=plan.step_index,
        step_capability=plan.step_capability,
        step_focus=plan.step_focus,
    )
    out.sync_step_from_plan()
    from casa.domain.wake_decompose import apply_wake_decompose

    return apply_wake_decompose(state, out)


def probe_gate_passed(report: dict[str, Any], gate_id: str = "") -> bool:
    """Honest lab gate — independent of route promote (see teacher_gate)."""
    from casa.domain.teacher_gate import probe_gate_passed as _teacher_probe_gate_passed

    return _teacher_probe_gate_passed(report, gate_id)


def _gate_corpus_whole(report: dict[str, Any]) -> bool:
    from casa.domain.teacher_gate import _gate_corpus_whole as _fn

    return _fn(report)


def _gate_analytic_r1(report: dict[str, Any]) -> bool:
    from casa.domain.teacher_gate import _gate_analytic_r1 as _fn

    return _fn(report)


def _actions_from_promote_hints(report: dict[str, Any]) -> list[dict[str, Any]]:
    raw = report.get("promote_hints") or report.get("promote_hint")
    if not raw:
        return []
    if isinstance(raw, dict):
        return [raw]
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    return []


def _probe_route_actions(report: dict[str, Any], gate_id: str, agent_id: str) -> list[dict[str, Any]]:
    """Known probe → capability/applicability routes (tests; production uses tick promote)."""
    probe = str(report.get("probe") or gate_id)
    if probe not in _BOOTSTRAP_PROBES:
        return []
    stage = str(report.get("stage") or "")
    locale = "ru"
    actions: list[dict[str, Any]] = []

    if probe in ("literacy-corpus-quiz",) or stage == "stage-06-words-cyrl-corpus":
        if not _gate_corpus_whole(report):
            return []
        actions.append(
            {
                "kind": "capability",
                "match": {"modality": "vis", "surface_class": "word", "trained_frame": "true"},
                "target_skill": "skill.read.whole",
            }
        )
        actions.append(
            {
                "kind": "goal",
                "match": {"inbox_kind": "literacy", "stage": "stage-06-words-cyrl-corpus"},
                "target_goal": "goal.learn.corpus",
            }
        )
        return actions

    if probe == "analytic-read-corpus-r1":
        if not _gate_analytic_r1(report):
            return []
        actions.append(
            {
                "kind": "capability",
                "match": {"modality": "vis", "surface_class": "word", "novel": "true"},
                "target_skill": "skill.read.analytic",
            }
        )
        actions.append(
            {
                "kind": "applicability",
                "match": {"goal": "goal.read.word", "locale": locale},
                "target_plan": f"plan.analytic_read_{agent_id}",
                "steps": ["skill.read.analytic", "skill.verify.lex"],
            }
        )
        return actions

    if probe == "phrase-compose-pilot":
        if not report.get("phrase_know"):
            return []
        actions.append(
            {
                "kind": "capability",
                "match": {"modality": "vis", "surface_class": "phrase", "locale": locale},
                "target_skill": "skill.read.phrase",
            }
        )
        return actions

    if probe == "phrase-agent-store":
        from casa.domain.teacher_gate import _gate_phrase_agent_store

        if not _gate_phrase_agent_store(report):
            return []
        actions.append(
            {
                "kind": "capability",
                "match": {"modality": "vis", "surface_class": "phrase", "locale": locale},
                "target_skill": "skill.read.phrase",
            }
        )
        actions.append(
            {
                "kind": "applicability",
                "match": {"goal": "goal.read.phrase", "locale": locale},
                "target_plan": f"plan.phrase_compose_{agent_id}",
                "steps": [
                    "skill.read.analytic",
                    "skill.compose.slots",
                    "skill.verify.phrase",
                ],
            }
        )
    return actions


def _collect_route_actions(
    report: dict[str, Any],
    gate_id: str,
    agent_id: str,
) -> list[dict[str, Any]]:
    hints = _actions_from_promote_hints(report)
    if hints:
        return hints
    return _probe_route_actions(report, gate_id, agent_id)


def _apply_route_actions(
    state: dict,
    actions: list[dict[str, Any]],
    *,
    gate_id: str,
    agent_id: str,
    result: PromoteResult,
) -> None:
    for action in actions:
        kind = action.get("kind")
        match = {str(k): str(v) for k, v in (action.get("match") or {}).items()}
        if kind == "capability":
            row = _safe_promote_capability(
                state,
                match=match,
                target_skill=str(action.get("target_skill") or ""),
                gate=gate_id,
                agent_id=agent_id,
            )
            if row:
                result.promoted.append(row)
            else:
                result.skipped.append(f"capability:{match}")
        elif kind == "applicability":
            row = _safe_promote_applicability(
                state,
                match=match,
                target_plan=str(action.get("target_plan") or ""),
                steps=list(action.get("steps") or []),
                gate=gate_id,
                agent_id=agent_id,
            )
            if row:
                result.promoted.append(row)
            else:
                result.skipped.append(f"applicability:{match}")
        elif kind == "goal":
            row = promote_goal_route(
                state,
                match=match,
                target_goal=str(action.get("target_goal") or ""),
                gate=gate_id,
                agent_id=agent_id,
            )
            if row:
                result.promoted.append(row)
            else:
                result.skipped.append(f"goal:{match}")


def record_probe_gate(
    state: dict,
    report: dict[str, Any],
    *,
    gate_id: str | None = None,
    tick: int = 0,
    store_dir: Path | None = None,
) -> PromoteResult:
    """Lab: gate verdict + mastery streak in state. No routes on field."""
    return promote_from_probe_report(
        state,
        report,
        gate_id=gate_id,
        tick=tick,
        store_dir=store_dir,
    )


def promote_from_probe_report(
    state: dict,
    report: dict[str, Any],
    *,
    gate_id: str | None = None,
    agent_id: str = "",
    tick: int = 0,
    store_dir: Path | None = None,
) -> PromoteResult:
    """Record probe gate pass + mastery streak. Does not write routes on field."""
    from casa.domain.deliberate_practice import weakest_link_from_probe_report
    from casa.domain.mastery_gate import record_gate_attempt, sync_probe_pass_to_skill_gate

    from casa.domain.teacher_gate import credits_mastery, gate_kind_for_probe

    gid = gate_id or str(report.get("probe") or "probe")
    kind = gate_kind_for_probe(gid, report)
    criteria_pass = probe_gate_passed(report, gid)
    if credits_mastery(kind):
        record_gate_attempt(state, gid, passed=criteria_pass, tick=tick, store_dir=store_dir)
        if criteria_pass:
            sync_probe_pass_to_skill_gate(state, gid, tick=tick, store_dir=store_dir)
    else:
        result = PromoteResult(gate=gid, passed=criteria_pass)
        result.skipped.append("sidecar_no_mastery_credit")
        if criteria_pass:
            _stash_probe_report(state, report)
        else:
            weak = weakest_link_from_probe_report(report)
            if weak:
                state.setdefault("last_weakest_link", weak)
        return result

    result = PromoteResult(gate=gid, passed=criteria_pass)
    if criteria_pass:
        _stash_probe_report(state, report)
    else:
        weak = weakest_link_from_probe_report(report)
        if weak:
            state.setdefault("last_weakest_link", weak)
    return result


def _stash_probe_report(state: dict, report: dict[str, Any]) -> None:
    probe = str(report.get("probe") or "").strip()
    if not probe:
        return
    sn = state.setdefault("sn", {})
    stash: dict[str, Any] = sn.setdefault("last_probe_reports", {})
    stash[probe] = {
        k: report[k]
        for k in (
            "probe",
            "phrase_know",
            "verdict",
            "know",
            "total",
            "empty",
            "wrong",
            "items",
            "event_id",
            "know_words",
            "total_words",
            "events",
            "event_ids",
            "phrase_know_count",
            "total_events",
        )
        if k in report
    }


def promote_pending_bootstrap_routes(
    state: dict,
    *,
    agent_id: str = "",
    min_mastery_streak: int = 2,
) -> list[PromoteResult]:
    """Apply bootstrap routes when probe mastery streak is ready (tick / lab closure)."""
    stash = (state.get("sn") or {}).get("last_probe_reports") or {}
    out: list[PromoteResult] = []
    for probe in sorted(_BOOTSTRAP_PROBES):
        report = stash.get(probe)
        if not isinstance(report, dict):
            continue
        row = promote_routes_from_probe_report(
            state,
            report,
            gate_id=probe,
            agent_id=agent_id,
            min_mastery_streak=min_mastery_streak,
        )
        if row.promoted:
            out.append(row)
    return out


def promote_routes_from_probe_report(
    state: dict,
    report: dict[str, Any],
    *,
    gate_id: str | None = None,
    agent_id: str = "",
    min_mastery_streak: int = 2,
) -> PromoteResult:
    """Apply capability/applicability routes when probe gate + mastery streak are ready."""
    from casa.domain.mastery_gate import mastery_ready, mastery_status

    aid = agent_id or agent_id_from_state(state)
    gid = gate_id or str(report.get("probe") or "probe")
    result = PromoteResult(gate=gid, passed=probe_gate_passed(report, gid))
    if not result.passed:
        return result

    actions = _collect_route_actions(report, gid, aid)
    if not actions:
        result.skipped.append("probe_route_actions_empty")
        return result

    status = mastery_status(state, gid, min_streak=min_mastery_streak)
    if not mastery_ready(state, gid, min_streak=min_mastery_streak):
        result.skipped.append(f"mastery_pending:{status['streak']}/{min_mastery_streak}")
        return result

    _apply_route_actions(state, actions, gate_id=gid, agent_id=aid, result=result)
    return result
