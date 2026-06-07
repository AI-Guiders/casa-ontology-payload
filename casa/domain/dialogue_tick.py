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
    if q:
        from casa.prisms.tick.semantic_read import route_kb_read
        from casa.prisms.shared.store_bundles import load_store_bundles

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

    arbiter = mem_prep.get("goal_arbiter") if isinstance(mem_prep.get("goal_arbiter"), dict) else {}
    disp = _parse_disposition(arbiter.get("subject_disposition"))
    load_rep = arbiter.get("load") if isinstance(arbiter.get("load"), dict) else {}

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
        ctx, reply_text = compose_subject_partner_reply_with_ctx(
            q, task, state, wm_next, store_dir=store_dir
        )
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
            },
        )
        out["outbound"].append(turn.to_dict())
        out["reply_text"] = reply_text
        out["wm_prism"] = wm_rep
        out["intent_prism"] = intent_rep

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


def apply_subject_answer_text(
    task: TaskEmit,
    *,
    user_query: str | None,
    state: dict,
    wm: WorkingMemory,
    store_dir: Path,
) -> str:
    """Replace CEN answer_text in report when subject mode active."""
    if not is_subject_mode(state, store_dir):
        return task.answer_text
    q = (user_query or "").strip()
    if not q:
        return task.answer_text
    return compose_subject_partner_reply(q, task, state, wm, store_dir=store_dir)
