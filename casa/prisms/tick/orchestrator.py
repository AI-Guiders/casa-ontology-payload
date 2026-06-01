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
from casa.prisms.control.sn_cen_runtime import cen_plan, digest_from_decoded, sn_route, task_to_dict
from casa.prisms.control.tick import ControlExtensions, run_control_extensions
from casa.prisms.memory.agent_bridges import load_agent_bridges, merge_digest_with_agent_bridges
from casa.prisms.memory.agent_prism import load_agent_prism
from casa.prisms.memory.memory_prisms import append_episode, ensure_prisms, memory_lattices, run_sleep
from casa.prisms.memory.stack import decode_lattice
from casa.prisms.shared.field_write import decode_field_grid, load_field_state
from casa.prisms.shared.canonical import CANONICAL_FIELD_MIN_VOTES
from casa.prisms.shared.prism_state import prism_hippo
from casa.prisms.shared.store_persist import mark_runtime_dirty
from casa.prisms.tick.act_rollout import act_rollout_phase, active_memory_lattice_id, merge_decoded_digests
from casa.prisms.tick.surprise_policy import (
    bump_episode_recurrence,
    find_predict_mismatch_episode,
    normalize_cue,
    should_skip_journal_surprise,
    surprise_signature,
)


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
    kolb_session: dict[str, Any] | None = None


def _load_bundle(store_dir: Path) -> dict | None:
    bs = list((store_dir / "bundles").glob("*.json"))
    if not bs:
        return None
    import json

    return json.loads(bs[0].read_text(encoding="utf-8"))


def surprise_to_hippo_episode(
    state: dict,
    *,
    control: ControlExtensions,
    wm: WorkingMemory,
    user_query: str | None,
    lattice_id: str,
    bundle: dict | None,
    min_value: float,
) -> dict | None:
    if not control.surprise or control.value < min_value:
        return None
    cue = (user_query or wm.goal or "macro_tick")[:120]
    norm = normalize_cue(cue)
    existing = find_predict_mismatch_episode(state, norm_cue=norm)
    if existing:
        updated = bump_episode_recurrence(existing)
        updated["cue"] = cue
        episodes = prism_hippo(state).get("episodes") or []
        for i, row in enumerate(episodes):
            if row.get("id") == existing.get("id"):
                episodes[i] = updated
                break
        mark_runtime_dirty(state)
        return updated

    predicted = ", ".join(control.predicted[:8]) or "?"
    observed = ", ".join(control.surprise[:8]) or "?"
    ep = append_episode(
        state,
        cue=cue,
        surface_attempt=predicted,
        correct=observed,
        lattice_id=lattice_id,
        bundle=bundle,
        scene="predict_surprise",
        structure_tag="predict_mismatch",
    )
    mark_runtime_dirty(state)
    return ep


def maybe_agent_remember_surprise(
    store_dir: Path,
    state: dict,
    *,
    control: ControlExtensions,
    concept_ids: list[str],
    min_value: float,
    user_query: str | None = None,
    wm: WorkingMemory | None = None,
) -> dict[str, Any] | None:
    if control.value < min_value or not control.surprise:
        return None
    sig = surprise_signature(control.surprise)
    if should_skip_journal_surprise(store_dir, sig=sig):
        return None
    cue = (user_query or (wm.goal if wm else "") or "macro_tick")[:120]
    norm = normalize_cue(cue)
    from casa.prisms.memory.agent_memory_ops import agent_remember

    return agent_remember(
        store_dir,
        state,
        {
            "kind": "observation",
            "text": (
                f"cue «{cue}»; predict mismatch: expected {', '.join(control.predicted[:5]) or '?'}; "
                f"surprise {', '.join(control.surprise[:5])}"
            ),
            "concepts": list(concept_ids[:8]),
            "tags": ["implicit", "surprise", f"cue:{norm[:48]}"],
            "data": {
                "prediction_error": control.prediction_error,
                "value": control.value,
                "surprise_signature": sig,
                "cue_normalized": norm,
            },
        },
        persist=False,
    )


def maybe_sleep_phase(
    state: dict,
    bundle: dict | None,
    *,
    sleep_every: int,
    sleep_on_value: float,
    control: ControlExtensions,
) -> dict[str, Any] | None:
    hippo = (state.get("prisms") or {}).get("prism_hippo") or {}
    episodes = [e for e in (hippo.get("episodes") or []) if not e.get("consolidated")]
    if not episodes:
        return None

    cons = state.setdefault("consolidation", {})
    ticks_since = int(cons.get("ticks_since_sleep") or 0) + 1
    cons["ticks_since_sleep"] = ticks_since

    do_sleep = sleep_every > 0 and ticks_since >= sleep_every
    if not do_sleep and control.value >= sleep_on_value:
        do_sleep = True
    if not do_sleep:
        return None

    rep = run_sleep(state, bundle)
    cons["ticks_since_sleep"] = 0
    mark_runtime_dirty(state)
    return rep


def _fallback_bundle(store_dir: Path) -> dict | None:
    bundle = _load_bundle(store_dir)
    if bundle is not None:
        return bundle
    if store_dir.name == "math-l0-lab":
        math_bundle = REPO_ROOT / "lab/exp_l/kb-math-concrete-schemas-l0.bundle.v1.json"
        if math_bundle.is_file():
            return json.loads(math_bundle.read_text(encoding="utf-8"))
    return None


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
) -> tuple[dict[str, Any], WorkingMemory, dict]:
    """One macro tick T with implicit learning loop closed."""
    cfg = config or LearningTickConfig()
    store_dir = store_dir.resolve()
    field_path = store_dir / "field_state.json"

    t0 = time.perf_counter()
    bundle_name, bundle, decoded, recovery, decode_ms, state = _load_tick_field(
        field_path, store_dir, min_votes=cfg.min_votes
    )
    routing_bundle = bundle if bundle is not None else {"claims": [], "graph": {"edges": []}}

    act_report: dict[str, Any] | None = None
    if cfg.act_rollout:
        act_report = act_rollout_phase(state, store_dir, device=cfg.act_device)
        extra = act_report.get("decoded")
        if extra:
            decoded = merge_decoded_digests(decoded, extra)

    load_agent_prism(store_dir, state)
    load_agent_bridges(store_dir, state)

    from casa.prisms.memory.prism_router import RouteContext, apply_route_to_sn, resolve_route

    store_meta = state.get("store") if isinstance(state.get("store"), dict) else {}
    route_ctx = RouteContext(
        modality="segment",
        locale=str(store_meta.get("locale") or ""),
        tier=str(store_meta.get("tier") or ""),
        store_id=store_dir.name,
    )
    route_target = resolve_route(state, route_ctx)
    apply_route_to_sn(state, route_target)

    digest = merge_digest_with_agent_bridges(digest_from_decoded(decoded), state)
    bias = salience_mode_bias(wm, digest.concept_ids)
    gated = sn_route(digest, bundle=routing_bundle, wm_mode=wm.mode, wm_salience_bias=bias)
    q = effective_user_query(wm, user_query)
    task = cen_plan(gated, bundle=routing_bundle, user_query=q)
    wm_next = fpn_after_cen(wm, task, user_query=q)

    control = run_control_extensions(
        prior_digest=wm.last_concepts,
        current_digest=digest.concept_ids,
        goal=[wm.goal] if wm.goal else digest.concept_ids[:8],
        task_relevant=bool(wm.goal or q),
    )

    bundle_for_hippo = bundle or _load_bundle(store_dir)
    lattice_id = active_memory_lattice_id(state)

    hippo_ep: dict | None = None
    if cfg.surprise_episode:
        hippo_ep = surprise_to_hippo_episode(
            state,
            control=control,
            wm=wm,
            user_query=q,
            lattice_id=lattice_id,
            bundle=bundle_for_hippo,
            min_value=cfg.surprise_min_value,
        )

    remember_rep: dict | None = None
    if cfg.remember_on_surprise:
        remember_rep = maybe_agent_remember_surprise(
            store_dir,
            state,
            control=control,
            concept_ids=digest.concept_ids,
            min_value=cfg.remember_min_value,
            user_query=q,
            wm=wm,
        )

    retain_rep: dict | None = None
    if cfg.retain_on_verified_predict and q and bundle_for_hippo:
        from casa.prisms.memory.agent_autonomous_retain import maybe_autonomous_retain_tick

        retain_rep = maybe_autonomous_retain_tick(
            store_dir,
            state,
            cue=q,
            bundle=bundle_for_hippo,
            persist=False,
        )

    sleep_rep: dict | None = None
    if cfg.sleep_every > 0 or cfg.sleep_on_value > 0:
        sleep_rep = maybe_sleep_phase(
            state,
            bundle_for_hippo,
            sleep_every=cfg.sleep_every,
            sleep_on_value=cfg.sleep_on_value,
            control=control,
        )

    kolb_rep: dict | None = None
    if cfg.kolb_session:
        from casa.prisms.hippo.kolb_cycle import kolb_cycle

        kolb_rep = kolb_cycle(state, cfg.kolb_session, bundle=bundle_for_hippo)

    wm_next.last_concepts = list(digest.concept_ids)
    state["sn"] = {
        **(state.get("sn") or {}),
        "last_tick": wm_next.tick,
        "last_sn_mode": gated.gate.mode,
        "kolb_phase": "active_experimentation" if kolb_rep else None,
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
        "kolb": kolb_rep,
        "learning_cycle": {
            "extract": {"field_decode": True, "act_rollout": bool(act_report and not act_report.get("skipped"))},
            "remember": {"hippo_episode": hippo_ep is not None, "sleep": sleep_rep is not None},
            "use": {"sn_cen": True, "explicit_remember": remember_rep is not None, "self_retain": retain_rep is not None},
        },
    }
    return report, wm_next, state
