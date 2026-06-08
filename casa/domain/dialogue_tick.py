#!/usr/bin/env python3
"""Dialogue organ hooks on macro tick (ADR-0045)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from casa.domain.dialogue_turn import (
    append_partner_turn,
    append_subject_turn,
    last_outbound_turn,
    load_dialogue_turns,
)
from casa.domain.subject_agency import SubjectAction, SubjectDisposition
from casa.domain.subject_mode import is_subject_mode, subject_display_name
from casa.domain.dialogue_provenance import meaning_provenance
from casa.domain.subject_voice import (
    compose_subject_partner_reply_with_ctx,
    initiate_from_autonomy,
    initiate_from_overload,
    initiate_from_retro,
    initiate_from_self_drive,
    verbalize_disposition,
)
from casa.prisms.control.fpn_state import WorkingMemory, read_session_meta, write_session_meta
from casa.prisms.control.sn_cen_runtime import TaskEmit


def _dialogue_can_answer_despite_defer(disp: SubjectDisposition | None, query_intent: str) -> bool:
    """A stale weak tract should not silence a direct partner turn."""
    from casa.prisms.memory.intent import is_agent_tract

    if is_agent_tract(query_intent):
        return True
    if disp is None or disp.action != SubjectAction.DEFER:
        return False
    if not disp.reason.startswith("tract_not_ready:"):
        return False
    return query_intent in {"social", "discuss", "rewrite", "grammar", "explain", "journal", "recall"}


def _parse_disposition(raw: dict[str, Any] | None) -> SubjectDisposition | None:
    if not raw or not raw.get("action"):
        return None
    try:
        action = SubjectAction(str(raw["action"]))
    except ValueError:
        return None
    return SubjectDisposition(
        action=action,
        reason=str(raw.get("reason") or ""),
        competing_source=str(raw.get("competing_source") or ""),
    )


def dialogue_initiate_from_wake_retro(store_dir: Path) -> dict[str, Any] | None:
    """After retrospective on wake — optional outbound turn."""
    meta = read_session_meta(store_dir)
    if meta.get("dialogue_retro_announced"):
        return None
    from casa.domain.agent_journal import last_retrospective

    retro = last_retrospective(store_dir)
    if not retro or retro.get("trigger") != "wake":
        return None
    text = initiate_from_retro(retro)
    if not text:
        return None
    turn = append_subject_turn(
        store_dir,
        text,
        kind="retro",
        provenance={"trigger": "wake_retro", "at": retro.get("at")},
    )
    meta["dialogue_retro_announced"] = retro.get("at")
    write_session_meta(store_dir, meta)
    return {"initiated": True, "kind": "retro", "turn": turn.to_dict()}


def _trim_reply_for_budget(text: str, state: dict) -> str:
    from casa.prisms.affect import affect_compose_bias
    from casa.prisms.metabolic import metabolic_compose_budget

    budget = metabolic_compose_budget(state)
    if budget is not None:
        scale = float(affect_compose_bias(state).get("budget_scale") or 1.0)
        try:
            from casa.prisms.neuromodulator import neuromodulator_compose_budget_scale

            scale *= neuromodulator_compose_budget_scale(state)
        except ImportError:
            pass
        budget = max(24, int(budget * scale))
    raw = (text or "").strip()
    if budget is None or len(raw) <= budget:
        return raw
    cut = raw[: budget - 1].rsplit(" ", 1)[0]
    return (cut or raw[: budget - 1]) + "…"


def process_dialogue_on_tick(
    store_dir: Path,
    state: dict,
    *,
    wm: WorkingMemory,
    wm_next: WorkingMemory,
    user_query: str | None,
    task: TaskEmit | None,
    mem_prep: dict[str, Any],
    self_drive_rep: dict[str, Any] | None = None,
    retro_rep: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append partner/subject turns; verbalize agency; initiate speech when due."""
    store_dir = store_dir.resolve()
    if not is_subject_mode(state, store_dir):
        return {"subject_mode": False, "turns_total": len(load_dialogue_turns(store_dir))}

    display = subject_display_name(state, store_dir)
    out: dict[str, Any] = {"subject_mode": True, "outbound": [], "partner": None}
    provenance_base = {
        "tick": wm_next.tick,
        "goal_id": wm_next.goal_id,
        "field_version": state.get("field_version"),
    }

    q = (user_query or "").strip()
    query_intent = ""
    metabolic_rep: dict[str, Any] = {}
    neuromod_rep: dict[str, Any] = {}
    pre_zone: dict[str, Any] = {}
    surprise_for_metabolic = 0

    arbiter = mem_prep.get("goal_arbiter") if isinstance(mem_prep.get("goal_arbiter"), dict) else {}
    disp = _parse_disposition(arbiter.get("subject_disposition"))
    load_rep = arbiter.get("load") if isinstance(arbiter.get("load"), dict) else {}

    if q:
        from casa.prisms.intelligence.executive import ensure_executive_zone, executive_before_compose
        from casa.prisms.intelligence.tick import intelligence_before_partner_compose
        from casa.prisms.metabolic import metabolic_begin_tick
        from casa.prisms.perceptual import perceptual_prepare_turn, perceptual_turn_hints
        from casa.prisms.tick.routing import route_kb_read
        from casa.prisms.shared.store_bundles import load_store_bundles

        metabolic_rep = metabolic_begin_tick(state, tick=int(wm_next.tick))
        perceptual_prepare_turn(state, q, modality="text_stream")
        prior_digest = list(wm.last_concepts or []) if wm.last_concepts else None
        executive_before_compose(
            state,
            query=q,
            concept_hints=perceptual_turn_hints(state),
            prior_digest=prior_digest,
        )
        surprise_for_metabolic = int(ensure_executive_zone(state).get("predict_surprise_n") or 0)
        try:
            from casa.prisms.neuromodulator import neuromodulator_begin_tick, neuromodulator_is_active

            if neuromodulator_is_active(state):
                neuromod_rep = neuromodulator_begin_tick(
                    state,
                    tick=int(wm_next.tick),
                    surprise_n=surprise_for_metabolic,
                )
        except ImportError:
            pass
        pre_zone = intelligence_before_partner_compose(
            state,
            partner_text=q,
            query_intent="",
            disposition=disp.action.value if disp else "",
            tick=int(wm_next.tick),
        )
        pre_read = route_kb_read(q, load_store_bundles(store_dir), store_dir=store_dir, state=state)
        query_intent = pre_read.intent
        ranked_tracts = list(pre_read.tract_ranked or [])
        partner = append_partner_turn(
            store_dir,
            q,
            provenance={
                **provenance_base,
                "source": "tick_query",
                "query_intent": pre_read.intent,
            },
        )
        out["partner"] = partner.to_dict()

    if (
        disp
        and disp.action in (SubjectAction.DEFER, SubjectAction.REFUSE)
        and not (q and _dialogue_can_answer_despite_defer(disp, query_intent))
    ):
        text = verbalize_disposition(disp, display_name=display, wm=wm_next)
        kind = "defer" if disp.action == SubjectAction.DEFER else "refuse"
        turn = append_subject_turn(
            store_dir,
            text,
            kind=kind,
            disposition=disp.action.value,
            provenance={**provenance_base, "reason": disp.reason, "source": "subject_agency"},
        )
        out["outbound"].append(turn.to_dict())
        out["disposition_verbalized"] = disp.action.value

    elif q:
        from casa.prisms.intelligence.tick import process_intelligence_turn

        ctx, reply_text = compose_subject_partner_reply_with_ctx(
            q, task, state, wm_next, store_dir=store_dir
        )
        reply_text = _trim_reply_for_budget(reply_text, state)
        sn = state.get("sn") if isinstance(state.get("sn"), dict) else {}
        surprise_before = int(sn.get("surprise") or 0) or None
        from casa.prisms.memory.wm import wm_after_partner_turn

        wm_rep = wm_after_partner_turn(
            state,
            store_dir,
            ctx,
            reply_text,
            tick=int(wm_next.tick),
            overloaded=bool(load_rep.get("overloaded")),
            query=q,
            surprise_before=surprise_before,
            surprise_after=surprise_before,
        )
        from casa.prisms.memory.intent import intent_after_partner_turn

        bind_top = max((int(b.get("score") or 0) for b in getattr(ctx, "blocks", []) or []), default=0)
        intent_rep = intent_after_partner_turn(
            state,
            q,
            query_intent or getattr(ctx, "query_intent", "") or "general",
            tick=int(wm_next.tick),
            ranked=ranked_tracts,
            bind_top=bind_top,
        )
        ctx.wm_edge_scores = dict(wm_rep.get("wm_edge_scores") or {})
        from casa.prisms.affect import affect_compose_bias

        zone_snap = process_intelligence_turn(
            state,
            partner_text=q,
            subject_reply=reply_text or "",
            query_intent=query_intent or getattr(ctx, "query_intent", "") or "",
            concept_hints=list(getattr(ctx, "concept_hints", None) or []),
            disposition=disp.action.value if disp else "",
            tick=int(wm_next.tick),
        )
        try:
            from casa.prisms.neuromodulator import neuromodulator_is_active, neuromodulator_snapshot

            if neuromodulator_is_active(state):
                neuromod_rep = neuromodulator_snapshot(state)
                zone_snap["neuromodulator"] = neuromod_rep
        except ImportError:
            pass
        from casa.prisms.metabolic import metabolic_end_tick, metabolic_should_sleep

        metabolic_rep = metabolic_end_tick(
            state,
            surprise_n=surprise_for_metabolic,
            compose_tokens=len((reply_text or "").split()),
            bind_blocks=len(getattr(ctx, "blocks", []) or []),
            had_partner_input=True,
        )
        emotional = zone_snap.get("emotional") or {}
        affect_rep: dict[str, Any] = {"axes": emotional.get("axes") or {}}
        if zone_snap.get("life_event"):
            affect_rep["event"] = zone_snap["life_event"]
        elif pre_zone.get("life_event"):
            affect_rep["event"] = pre_zone["life_event"]
        else:
            affect_rep["bias"] = affect_compose_bias(state)
        if reply_text.strip():
            turn = append_subject_turn(
                store_dir,
                reply_text,
                kind="reply",
                provenance={
                    **provenance_base,
                    "source": "partner_reply",
                    "cen_action": task.action if task else "",
                    "yielded_disposition": disp.reason if disp else "",
                    **meaning_provenance(ctx),
                    "emotional_zone": affect_rep,
                    "intelligence_zones": {**zone_snap, "pre_compose": pre_zone},
                    "metabolic_zone": metabolic_rep,
                    "neuromodulator_zone": neuromod_rep or None,
                },
            )
            out["outbound"].append(turn.to_dict())
        else:
            # Empty compose: do not persist an empty subject turn (load_dialogue_turns
            # would silently drop it, leaving a stale prior outbound to be echoed).
            out["soft_miss"] = True
            out["reason"] = "empty_compose"
        out["reply_text"] = reply_text
        out["wm_prism"] = wm_rep
        out["intent_prism"] = intent_rep
        out["emotional_zone"] = affect_rep
        out["intelligence_zones"] = {**zone_snap, "pre_compose": pre_zone}
        out["metabolic_zone"] = metabolic_rep
        out["neuromodulator_zone"] = neuromod_rep or None
        out["forced_sleep"] = metabolic_should_sleep(state)

    else:
        initiated: list[dict[str, Any]] = []
        seed = mem_prep.get("autonomy_seed") if isinstance(mem_prep.get("autonomy_seed"), dict) else None
        text = initiate_from_autonomy(seed or {}, display_name=display) if seed else None
        if text:
            turn = append_subject_turn(
                store_dir,
                text,
                kind="initiate",
                provenance={**provenance_base, "source": "autonomy_seed"},
            )
            initiated.append(turn.to_dict())

        if not initiated and load_rep.get("overloaded"):
            turn = append_subject_turn(
                store_dir,
                initiate_from_overload(),
                kind="initiate",
                disposition="defer",
                provenance={**provenance_base, "source": "overload"},
            )
            initiated.append(turn.to_dict())

        if not initiated and retro_rep:
            text = initiate_from_retro(retro_rep)
            if text:
                turn = append_subject_turn(
                    store_dir,
                    text,
                    kind="retro",
                    provenance={**provenance_base, "source": "after_sleep_retro"},
                )
                initiated.append(turn.to_dict())

        if not initiated and self_drive_rep:
            text = initiate_from_self_drive(self_drive_rep)
            if text:
                turn = append_subject_turn(
                    store_dir,
                    text,
                    kind="initiate",
                    provenance={**provenance_base, "source": "self_drive"},
                )
                initiated.append(turn.to_dict())

        out["outbound"].extend(initiated)
        out["initiated"] = bool(initiated)

    last = last_outbound_turn(store_dir)
    out["turns_total"] = len(load_dialogue_turns(store_dir))
    out["last_outbound"] = last.to_dict() if last else None
    return out
