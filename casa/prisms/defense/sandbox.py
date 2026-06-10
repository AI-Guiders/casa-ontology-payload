#!/usr/bin/env python3
"""Defense sandbox — rechannel experiments before core promote (ADR-0076 P20b)."""

from __future__ import annotations

from typing import Any

from casa.prisms.defense.core import defense_block
from casa.prisms.defense.model import RechannelExperiment
from casa.prisms.intelligence.defense_zone import SANDBOX_PREFIX, ensure_defense_zone


def _tract_to_proxy_prefix(tract: str) -> str:
    key = str(tract or "").strip().lower()
    if key in ("math", "schema", "predict"):
        return "math."
    if key in ("grammar", "linguistic"):
        return "ru.grammar."
    if key in ("logical", "explain"):
        return "ru.prop."
    if key in ("social", "discuss"):
        return "agent.social."
    return "agent.affect."


def _tract_to_domain_tract(tract: str) -> tuple[str, str]:
    key = str(tract or "").strip().lower()
    if key in ("math", "schema", "predict"):
        return "math", "math"
    if key in ("grammar", "linguistic"):
        return "linguistic", "grammar"
    if key in ("logical", "explain"):
        return "logical", "explain"
    if key in ("social", "discuss"):
        return "social", "discuss"
    return "emotional", "general"


def _latest_threat_cues(state: dict) -> list[str]:
    block = defense_block(state)
    edges = block.get("trauma_edges") or []
    if isinstance(edges, list):
        for edge in reversed(edges):
            if isinstance(edge, dict) and edge.get("threat_cues"):
                return [str(c) for c in edge["threat_cues"]]
    history = block.get("trauma_last") or []
    if isinstance(history, list):
        for row in reversed(history):
            if not isinstance(row, dict):
                continue
            edge = row.get("edge")
            if isinstance(edge, dict) and edge.get("threat_cues"):
                return [str(c) for c in edge["threat_cues"]]
    from casa.prisms.defense.trauma_cement import extract_threat_cues

    return extract_threat_cues("страх боль")


def sandbox_record_rechannel(
    state: dict,
    *,
    threat_cues: list[str] | None = None,
    proxy_prefixes: list[str] | None = None,
    rechannel_domain: str = "",
    rechannel_tract: str = "",
    tick: int = 0,
    note: str = "",
    score: float = 0.0,
    mechanism: str = "rechannel",
    lattice_id: str = "",
) -> RechannelExperiment:
    """Agent drafts rechannel in sandbox — does not touch core trauma edges."""
    zone = ensure_defense_zone(state)
    sandbox = zone.setdefault("sandbox", {})
    policy = zone.get("zone_policy") or {}
    max_exp = int(policy.get("max_experiments") or 32)
    experiments: list[dict[str, Any]] = list(sandbox.get("experiments") or [])
    next_id = int(sandbox.get("next_experiment_id") or 1)
    exp_id = f"rch-{next_id}"
    cues = [str(c).strip().lower() for c in (threat_cues or _latest_threat_cues(state)) if str(c).strip()]
    tract = str(rechannel_tract or "math").strip().lower()
    domain = str(rechannel_domain or "").strip().lower()
    if not domain:
        domain, tract = _tract_to_domain_tract(tract)
    prefixes = [str(p) for p in (proxy_prefixes or [_tract_to_proxy_prefix(tract)]) if str(p).strip()]
    row = RechannelExperiment(
        experiment_id=exp_id,
        tick=int(tick),
        threat_cues=cues,
        proxy_prefixes=prefixes,
        rechannel_domain=domain,
        rechannel_tract=tract,
        note=str(note or "").strip()[:240],
        score=float(score),
        mechanism=str(mechanism or "rechannel"),
        lattice_id=str(lattice_id or ""),
    )
    experiments.append(row.to_dict())
    if len(experiments) > max_exp:
        experiments = experiments[-max_exp:]
    sandbox["experiments"] = experiments
    sandbox["next_experiment_id"] = next_id + 1
    defense_block(state)["sandbox_rechannel_last"] = row.to_dict()
    return row


def sandbox_bump_rechannel_score(
    state: dict,
    *,
    tract: str,
    delta: float = 0.18,
    tick: int = 0,
) -> dict[str, Any]:
    """Deliberate practice nudges open sandbox experiments toward promote."""
    zone = ensure_defense_zone(state)
    sandbox = zone.get("sandbox") or {}
    experiments = list(sandbox.get("experiments") or [])
    prefix = _tract_to_proxy_prefix(tract)
    bumped = 0
    for row in experiments:
        if not isinstance(row, dict) or row.get("promoted"):
            continue
        prefixes = [str(p) for p in (row.get("proxy_prefixes") or [])]
        if prefix not in prefixes and not any(p.startswith(prefix) for p in prefixes):
            continue
        row["score"] = round(float(row.get("score") or 0.0) + float(delta), 4)
        bumped += 1
    sandbox["experiments"] = experiments
    rep = {"bumped": bumped, "tract": tract, "tick": int(tick)}
    defense_block(state)["sandbox_bump_last"] = rep
    return rep


def promote_rechannel_experiment(state: dict, experiment_id: str, *, tick: int = 0) -> dict[str, Any] | None:
    """Promote scored sandbox rechannel → core trauma edge."""
    zone = ensure_defense_zone(state)
    policy = zone.get("zone_policy") or {}
    theta = float(policy.get("promote_theta") or 0.65)
    sandbox = zone.get("sandbox") or {}
    experiments = list(sandbox.get("experiments") or [])
    target: dict[str, Any] | None = None
    for row in experiments:
        if str(row.get("experiment_id") or row.get("id")) == str(experiment_id):
            target = row
            break
    if not target or target.get("promoted"):
        return None
    score = float(target.get("score") or 0.0)
    lattice_id = str(target.get("lattice_id") or "")
    if lattice_id:
        from casa.prisms.defense.lattice import lattice_evidence_score

        evidence = lattice_evidence_score(state, lattice_id)
        if evidence <= 0.0:
            return {
                "promoted": False,
                "reason": "no_lattice_evidence",
                "lattice_id": lattice_id,
            }
        score = min(1.0, score + evidence * 0.12)
    if score < theta:
        return {"promoted": False, "reason": "score_below_theta", "score": score, "theta": theta}

    from casa.prisms.defense.trauma_cement import promote_rechannel_to_core

    core_rep = promote_rechannel_to_core(
        state,
        threat_cues=[str(c) for c in (target.get("threat_cues") or [])],
        proxy_prefixes=[str(p) for p in (target.get("proxy_prefixes") or [])],
        rechannel_domain=str(target.get("rechannel_domain") or "math"),
        rechannel_tract=str(target.get("rechannel_tract") or "math"),
        tick=int(tick or target.get("tick") or 0),
        event="sandbox_promote",
        strength_delta=0.22 + min(0.15, score * 0.1),
    )
    target["promoted"] = True
    target["promoted_tick"] = int(tick)
    sandbox["experiments"] = experiments
    rep = {
        "promoted": True,
        "experiment_id": experiment_id,
        "score": score,
        "core": core_rep,
    }
    defense_block(state)["rechannel_promote_last"] = rep
    return rep


def try_auto_promote_rechannel_experiments(state: dict, *, tick: int = 0) -> list[dict[str, Any]]:
    """Promote all sandbox experiments that crossed promote_theta."""
    zone = ensure_defense_zone(state)
    sandbox = zone.get("sandbox") or {}
    promoted: list[dict[str, Any]] = []
    for row in list(sandbox.get("experiments") or []):
        if not isinstance(row, dict) or row.get("promoted"):
            continue
        eid = str(row.get("experiment_id") or "")
        if not eid:
            continue
        rep = promote_rechannel_experiment(state, eid, tick=tick)
        if rep and rep.get("promoted"):
            promoted.append(rep)
    return promoted


def defense_sandbox_on_sublimation_defer(
    state: dict,
    wm,
    *,
    tick: int = 0,
) -> dict[str, Any]:
    """Record sandbox rechannel draft when sublimation defers to deliberate practice."""
    from casa.prisms.defense.lattice import place_defense_rechannel_edge, spawn_defense_scratch_lattice

    capability = str(getattr(wm, "step_capability", "") or "").strip().lower()
    domain, tract = _tract_to_domain_tract(capability or "math")
    cues = _latest_threat_cues(state)
    proxy_prefix = _tract_to_proxy_prefix(tract)
    lid = spawn_defense_scratch_lattice(state, tick=tick, topic_slug=tract or "rechannel")
    threat_cid = f"{SANDBOX_PREFIX}threat.{cues[0]}" if cues else f"{SANDBOX_PREFIX}threat.cue"
    proxy_cid = f"{proxy_prefix}rechannel.{tract or 'practice'}"
    edge_rep = place_defense_rechannel_edge(
        state,
        threat_concept=threat_cid,
        proxy_concept=proxy_cid,
        tick=tick,
        lattice_id=lid,
    )
    row = sandbox_record_rechannel(
        state,
        threat_cues=cues,
        proxy_prefixes=[proxy_prefix],
        rechannel_domain=domain,
        rechannel_tract=tract,
        tick=tick,
        note="sublimation_defer",
        score=0.12,
        mechanism="sublimation",
        lattice_id=lid,
    )
    return {
        "recorded": True,
        "experiment_id": row.experiment_id,
        "tract": tract,
        "lattice_id": lid,
        "edge": edge_rep.get("edge_id"),
    }
