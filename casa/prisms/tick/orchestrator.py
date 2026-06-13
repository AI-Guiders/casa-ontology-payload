#!/usr/bin/env python3
"""
TickOrchestrator — unified macro tick: decode → act rollout → SN/CEN → surprise/hippo → sleep.

Maps to Understanding Contract (predict/surprise) and ADR-0015 (implicit + optional explicit remember).
Kolb cycle runs as optional batch hook (--kolb-session), not on every tick.
"""

from __future__ import annotations

from casa._paths import REPO_ROOT, ensure_import_paths

ensure_import_paths()

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from casa.prisms.control.fpn_state import WorkingMemory, effective_user_query, fpn_after_cen, salience_mode_bias
from casa.prisms.control.sn_cen_infer import _run_from_field
from casa.prisms.control.sn_cen_runtime import cen_plan, digest_from_decoded, sn_route, task_to_dict, TaskEmit
from casa.prisms.control.tick import ControlExtensions, run_control_extensions
from casa.prisms.memory.agent_bridges import load_agent_bridges, merge_digest_with_agent_bridges
from casa.prisms.memory.agent_prism import load_agent_prism
from casa.prisms.memory.memory_prisms import ensure_prisms, memory_lattices
from casa.prisms.memory.stack import decode_lattice
from casa.prisms.shared.field_write import decode_field_grid, load_field_state
from casa.prisms.shared.canonical import CANONICAL_FIELD_MIN_VOTES
from casa.prisms.shared.store_persist import mark_runtime_dirty
from casa.prisms.tick.act_rollout import act_rollout_phase, active_memory_lattice_id, merge_decoded_digests


@dataclass(frozen=True, slots=True)
class LearningTickConfig:
    min_votes: int = CANONICAL_FIELD_MIN_VOTES
    act_rollout: bool = True
    act_device: str = "cpu"
    surprise_episode: bool = True
    surprise_min_value: float = 0.3
    remember_on_surprise: bool = True
    remember_min_value: float = 0.45
    retain_on_verified_predict: bool = True
    sleep_every: int = 0
    sleep_on_value: float = 1.0
    compact_persist_on_sleep: bool = False
    sleep_batch_size: int = 0
    kolb_session: dict[str, Any] | None = None
    kolb_relink_on_surprise: bool = True
    kolb_relink_min_value: float = 0.4
    agent_self_drive: bool = True
    agent_self_drive_min_value: float = 0.25
    goal_from_surprise: bool = True
    metacog_gate: bool = True
    spacing_on_wake: bool = True
    tick_log: bool = True
    tick_log_max: int = 64
    retro_after_sleep: bool = True


def _load_bundle(store_dir: Path) -> dict | None:
    from casa.prisms.shared.store_bundles import load_store_bundle

    return load_store_bundle(store_dir)


def _fallback_bundle(store_dir: Path) -> dict | None:
    bundle = _load_bundle(store_dir)
    if bundle is not None:
        return bundle
    if store_dir.name == "math-l0-lab":
        math_bundle = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
        if math_bundle.is_file():
            return json.loads(math_bundle.read_text(encoding="utf-8"))
    return None


def _decode_tick_field(
    state: dict,
    store_dir: Path,
    *,
    min_votes: int,
) -> tuple[str, dict, dict, dict, float]:
    """Decode already-loaded field state (no disk load)."""
    t0 = time.perf_counter()
    state = ensure_prisms(state)
    decoded: dict[str, Any] = {"concepts": {}, "tokens": {}}
    try:
        decoded = decode_field_grid(state, min_votes=min_votes)
    except ValueError:
        pass
    lats = memory_lattices(state)
    lid = active_memory_lattice_id(state)
    if lid in lats:
        decoded = merge_decoded_digests(decoded, decode_lattice(lats[lid], min_votes=1))
    elif lats:
        for lat in lats.values():
            decoded = merge_decoded_digests(decoded, decode_lattice(lat, min_votes=1))
    bundle = _fallback_bundle(store_dir)
    ms = (time.perf_counter() - t0) * 1000
    return "memory_field", bundle or {"claims": [], "graph": {"edges": []}}, decoded, {}, ms


def _load_tick_field(
    field_path: Path,
    store_dir: Path,
    *,
    min_votes: int,
) -> tuple[str, dict, dict, dict, float, dict]:
    """DMN grid path, or memory/F0 field when store has no bundles/."""
    try:
        return _run_from_field(field_path, store_dir, min_votes=min_votes)
    except (ValueError, FileNotFoundError):
        t0 = time.perf_counter()
        state = ensure_prisms(load_field_state(field_path))
        decoded: dict[str, Any] = {"concepts": {}, "tokens": {}}
        try:
            decoded = decode_field_grid(state, min_votes=min_votes)
        except ValueError:
            pass
        lats = memory_lattices(state)
        lid = active_memory_lattice_id(state)
        if lid in lats:
            decoded = merge_decoded_digests(decoded, decode_lattice(lats[lid], min_votes=1))
        elif lats:
            for lat in lats.values():
                decoded = merge_decoded_digests(decoded, decode_lattice(lat, min_votes=1))
        bundle = _fallback_bundle(store_dir)
        ms = (time.perf_counter() - t0) * 1000
        return "memory_field", bundle, decoded, {}, ms, state


def run_learning_tick(
    *,
    store_dir: Path,
    user_query: str | None,
    wm: WorkingMemory,
    config: LearningTickConfig | None = None,
    state: dict | None = None,
) -> tuple[dict[str, Any], WorkingMemory, dict]:
    """One macro tick T with implicit learning loop closed."""
    cfg = config or LearningTickConfig()
    store_dir = store_dir.resolve()
    field_path = store_dir / "field_state.json"
    t0 = time.perf_counter()
    from casa.nervous.impulse import impulse_recorder
    from casa.nervous.channels import ImpulseChannel, ImpulseOutcome

    rec = impulse_recorder()
    next_tick = int(wm.tick) + 1
    rec.begin_tick(next_tick, store_dir)

    if state is not None:
        bundle_name, bundle, decoded, recovery, decode_ms = _decode_tick_field(
            state, store_dir, min_votes=cfg.min_votes
        )
    else:
        bundle_name, bundle, decoded, recovery, decode_ms, state = _load_tick_field(
            field_path, store_dir, min_votes=cfg.min_votes
        )
        _ = bundle_name
    routing_bundle = bundle if bundle is not None else {"claims": [], "graph": {"edges": []}}

    act_report: dict[str, Any] | None = None
    if cfg.act_rollout:
        act_report = act_rollout_phase(state, store_dir, device=cfg.act_device)
        extra = act_report.get("decoded")
        if extra:
            decoded = merge_decoded_digests(decoded, extra)

    load_agent_prism(store_dir, state)
    load_agent_bridges(store_dir, state)

    from casa.prisms.memory.prism_router import tick_prepare_memory

    q_preview = effective_user_query(wm, user_query)
    from casa.domain.partner_cue_policy import prepare_wm_for_partner_cue

    prepare_wm_for_partner_cue(wm, q_preview or "")
    mem_prep = tick_prepare_memory(
        state, cue=q_preview or "", modality="segment", wm=wm, store_dir=store_dir
    )
    route_target = mem_prep["route"]
    routing_chain = mem_prep.get("routing_chain")
    plan_tick = mem_prep.get("plan_tick")

    from casa.prisms.tick.self_check_tick import maybe_self_check_before_cen

    self_check_rep = maybe_self_check_before_cen(
        state,
        wm=wm,
        mem_prep=mem_prep,
        cue=q_preview or "",
        bundle=routing_bundle,
    )

    digest = merge_digest_with_agent_bridges(digest_from_decoded(decoded), state)
    bias = salience_mode_bias(wm, digest.concept_ids)
    gated = sn_route(digest, bundle=routing_bundle, wm_mode=wm.mode, wm_salience_bias=bias)
    q = effective_user_query(wm, user_query)
    task = cen_plan(gated, bundle=routing_bundle, user_query=q)
    wm_next = fpn_after_cen(wm, task, user_query=q)

    if rec.is_active:
        with rec.channel(ImpulseChannel.CONTROL_ROUTING, store_dir=store_dir) as control_imp:
            control_imp.route(
                "sn_route",
                inputs={
                    "sn_mode": gated.gate.mode,
                    "wm_mode": wm.mode,
                    "surprise": bool(getattr(gated.gate, "surprise", False)),
                },
                selected=[str(gated.gate.mode)],
            )
            control_imp.select(
                "cen_plan",
                zone="executive",
                selected=[str(task.action or "")],
                inputs={
                    "intent": str(task.intent or ""),
                    "confidence": float(task.confidence or 0.0),
                },
            )
            route_outcome = ImpulseOutcome.NO_OP
            if task.action and task.action not in {"silent", "noop"}:
                route_outcome = ImpulseOutcome.MODE_CHANGED
            control_imp.finish(route_outcome, zones_touched=["executive"])

    from casa.prisms.memory.forgetting import memory_wake_forgetting_hooks

    wake_forget_rep = memory_wake_forgetting_hooks(state, tick=int(wm_next.tick))

    from casa.domain.dialogue_tick import process_dialogue_on_tick

    control = run_control_extensions(
        prior_digest=wm.last_concepts,
        current_digest=digest.concept_ids,
        goal=[wm.goal] if wm.goal else digest.concept_ids[:8],
        task_relevant=bool(wm.goal or q),
    )
    from casa.domain.partner_cue_policy import adjust_control_for_partner_cue

    control = adjust_control_for_partner_cue(q or "", control, bundle=routing_bundle)

    bundle_for_hippo = bundle or _load_bundle(store_dir)
    lattice_id = active_memory_lattice_id(state)

    from casa.domain.pdca_cycle import infer_pdca_phase
    from casa.domain.spacing_policy import record_spacing_seen
    from casa.prisms.control.session_log import append_tick_log
    from casa.prisms.tick.pdca_check_tick import PdcaCheckConfig, PdcaCheckContext, maybe_pdca_check_tick

    pdca_check_rep = maybe_pdca_check_tick(
        PdcaCheckContext(
            store_dir=store_dir,
            state=state,
            wm=wm_next,
            control=control,
            cue=q or "",
            lattice_id=lattice_id,
            bundle=bundle_for_hippo,
            mem_prep=mem_prep,
            cfg=PdcaCheckConfig(
                surprise_episode=cfg.surprise_episode,
                surprise_min_value=cfg.surprise_min_value,
                goal_from_surprise=cfg.goal_from_surprise,
                metacog_gate=cfg.metacog_gate,
            ),
        )
    )
    hippo_ep = pdca_check_rep.get("hippo_episode")
    if digest.concept_ids:
        record_spacing_seen(
            state,
            digest.concept_ids[0],
            tick=wm_next.tick,
            passed=bool(pdca_check_rep.get("check_passed")),
        )

    from casa.prisms.tick.pdca_act_tick import PdcaActConfig, PdcaActContext, maybe_pdca_act_tick

    pdca_act_rep = maybe_pdca_act_tick(
        PdcaActContext(
            store_dir=store_dir,
            state=state,
            wm=wm,
            wm_next=wm_next,
            control=control,
            mem_prep=mem_prep,
            cue=q or "",
            bundle=bundle_for_hippo,
            hippo_ep=hippo_ep,
            concept_ids=tuple(digest.concept_ids),
            cfg=PdcaActConfig(
                remember_on_surprise=cfg.remember_on_surprise,
                remember_min_value=cfg.remember_min_value,
                retain_on_verified_predict=cfg.retain_on_verified_predict,
                sleep_every=cfg.sleep_every,
                sleep_on_value=cfg.sleep_on_value,
                compact_persist_on_sleep=cfg.compact_persist_on_sleep,
                sleep_batch_size=cfg.sleep_batch_size,
                kolb_relink_on_surprise=cfg.kolb_relink_on_surprise,
                kolb_relink_min_value=cfg.kolb_relink_min_value,
                agent_self_drive=cfg.agent_self_drive,
                agent_self_drive_min_value=cfg.agent_self_drive_min_value,
                surprise_min_value=cfg.surprise_min_value,
            ),
        )
    )
    remember_rep = pdca_act_rep.get("remember")
    retain_rep = pdca_act_rep.get("retain")
    sleep_rep = pdca_act_rep.get("sleep")
    kolb_relink_rep = pdca_act_rep.get("adjust")
    self_drive_rep = pdca_act_rep.get("self_drive")
    pdca_act = pdca_act_rep.get("act_kind")

    kolb_rep: dict | None = None
    if cfg.act_rollout and rec.is_active and act_report and not act_report.get("skipped"):
        with rec.channel(ImpulseChannel.MOTOR_COMPOSE, store_dir=store_dir) as motor_imp:
            motor_imp.route(
                "act_rollout",
                zone="perceptual",
                inputs={"device": cfg.act_device, "decoded_keys": list((act_report.get("decoded") or {}).keys())[:6]},
            )
            motor_imp.finish(
                ImpulseOutcome.COMPOSED if act_report.get("decoded") else ImpulseOutcome.NO_OP,
                zones_touched=["perceptual"],
            )

    if sleep_rep and rec.is_active:
        with rec.channel(ImpulseChannel.SLEEP_TRAIN, store_dir=store_dir) as sleep_imp:
            sleep_imp.route(
                "sleep_boundary",
                zone="memory",
                inputs={"batch_size": cfg.sleep_batch_size, "compact": cfg.compact_persist_on_sleep},
            )
            sleep_imp.finish(ImpulseOutcome.QUEUED, zones_touched=["memory"])

    if cfg.kolb_session:
        from casa.prisms.hippo.kolb_cycle import kolb_cycle

        kolb_rep = kolb_cycle(state, cfg.kolb_session, bundle=bundle_for_hippo)

    retro_rep: dict[str, Any] | None = None
    wm_sleep_rep: dict[str, Any] | None = None
    intent_sleep_rep: dict[str, Any] | None = None
    if sleep_rep and cfg.retro_after_sleep:
        from casa.domain.subject_retrospective import maybe_run_retrospective_after_sleep

        retro_rep = maybe_run_retrospective_after_sleep(store_dir)

    if sleep_rep:
        from casa.prisms.memory.intent import intent_on_sleep_boundary
        from casa.prisms.memory.wm import wm_on_sleep_boundary

        wm_sleep_rep = wm_on_sleep_boundary(state, store_dir)
        intent_sleep_rep = intent_on_sleep_boundary(state, store_dir)

    dialogue_rep = process_dialogue_on_tick(
        store_dir,
        state,
        wm=wm,
        wm_next=wm_next,
        user_query=q,
        task=task,
        mem_prep=mem_prep,
        self_drive_rep=self_drive_rep,
        retro_rep=retro_rep,
    )
    if dialogue_rep.get("subject_mode") and dialogue_rep.get("reply_text"):
        task = TaskEmit(
            intent=task.intent,
            action=task.action,
            concepts=task.concepts,
            edges=task.edges,
            targets=task.targets,
            query_to_dmn=task.query_to_dmn,
            confidence=task.confidence,
            notes=task.notes,
            llm_probe=task.llm_probe,
            answer_blocks=task.answer_blocks,
            answer_text=str(dialogue_rep["reply_text"]),
        )

    pdca_phase = infer_pdca_phase(
        plan_tick=plan_tick,
        control=control.to_dict(),
        kolb_revised=bool(kolb_relink_rep and not kolb_relink_rep.get("skipped")),
        skill_promoted=bool(
            self_drive_rep
            and (self_drive_rep.get("skill_promote") or {}).get("promoted")
        ),
        sleep_ran=sleep_rep is not None,
    )

    wm_next.last_concepts = list(digest.concept_ids)
    state["sn"] = {
        **(state.get("sn") or {}),
        "last_tick": wm_next.tick,
        "last_sn_mode": gated.gate.mode,
        "kolb_phase": "active_experimentation" if kolb_rep else None,
        "pdca_phase": pdca_phase.value,
        "pdca_act": pdca_act,
        "metacog": (pdca_check_rep.get("metacog") or {}).get("scaffold_level"),
    }
    if kolb_rep:
        state["sn"]["mode"] = "wake"
    mark_runtime_dirty(state)

    wall_ms = round((time.perf_counter() - t0) * 1000, 2)
    report: dict[str, Any] = {
        "tick": wm_next.tick,
        "query": q,
        "wall_ms": wall_ms,
        "decode_ms": round(decode_ms, 2),
        "decode_source": bundle_name,
        "route": {
            "content_prism": route_target.prism_id,
            "lattice_hint": route_target.lattice_hint,
            "matched": route_target.matched,
        },
        "routing_chain": routing_chain.to_dict() if routing_chain is not None else None,
        "plan_tick": plan_tick,
        "field_version": state.get("field_version"),
        "recovery_concepts_f1": (recovery or {}).get("concepts", {}).get("f1"),
        "sn_mode": gated.gate.mode,
        "cen": task_to_dict(task, fpn=wm_next.to_dict()),
        "control": control.to_dict(),
        "act_rollout": act_report,
        "hippo_episode": hippo_ep,
        "agent_remember": remember_rep,
        "agent_retain": retain_rep,
        "sleep": sleep_rep,
        "retrospective": retro_rep,
        "kolb": kolb_rep,
        "kolb_relink": kolb_relink_rep,
        "agent_self_drive": self_drive_rep,
        "pdca": {
            "phase": pdca_phase.value,
            "act": pdca_act,
            "check_tick": pdca_check_rep,
            "act_tick": pdca_act_rep,
        },
        "spacing_goal": mem_prep.get("spacing_goal"),
        "progression_goal": mem_prep.get("progression_goal"),
        "scaffold_level": pdca_check_rep.get("scaffold_level"),
        "goal_emergent": pdca_check_rep.get("goal_emergent"),
        "deliberate_practice": pdca_check_rep.get("deliberate_practice"),
        "metacog": pdca_check_rep.get("metacog"),
        "self_organization": {
            "plan_arbiter": mem_prep.get("goal_arbiter"),
            "check_arbiter": pdca_check_rep.get("goal_arbiter"),
            "hypothesis": pdca_check_rep.get("hypothesis"),
            "self_model": pdca_check_rep.get("self_model_summary"),
            "cognitive_load": (mem_prep.get("goal_arbiter") or {}).get("load")
            or (pdca_check_rep.get("goal_arbiter") or {}).get("load"),
            "autonomy_seed": mem_prep.get("autonomy_seed"),
            "self_check": self_check_rep,
        },
        "memory_wake_forgetting": wake_forget_rep,
        "dialogue": dialogue_rep,
        "wm_prism_sleep": wm_sleep_rep,
        "intent_prism_sleep": intent_sleep_rep,
        "learning_cycle": {
            "extract": {"field_decode": True, "act_rollout": bool(act_report and not act_report.get("skipped"))},
            "remember": {"hippo_episode": hippo_ep is not None, "sleep": sleep_rep is not None},
            "reflect": {"retrospective": retro_rep is not None},
            "use": {
                "sn_cen": True,
                "explicit_remember": remember_rep is not None,
                "self_retain": retain_rep is not None,
                "kolb_relink": kolb_relink_rep is not None and not kolb_relink_rep.get("skipped"),
                "agent_self_drive": self_drive_rep is not None,
            },
        },
    }
    impulse_summaries = rec.end_tick()
    if impulse_summaries:
        report["impulse"] = impulse_summaries
    if cfg.tick_log:
        append_tick_log(store_dir, wm=wm_next, report=report, max_entries=cfg.tick_log_max)
        from casa.domain.experience_ledger import record_experience_from_tick

        record_experience_from_tick(store_dir, wm=wm_next, report=report)
        from casa.domain.skill_trace import record_skill_trace_from_tick

        record_skill_trace_from_tick(store_dir, wm=wm_next, report=report)

    from casa.domain.intent_checkpoint import save_intent_checkpoint

    if wm_next.goal_id or wm_next.step_capability:
        save_intent_checkpoint(
            store_dir,
            wm_next,
            why=q or wm_next.goal_id or "macro_tick",
            tick=wm_next.tick,
        )
    return report, wm_next, state
