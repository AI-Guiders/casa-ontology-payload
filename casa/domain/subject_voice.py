#!/usr/bin/env python3
"""Subject voice — verbalize disposition and partner replies (ADR-0045)."""

from __future__ import annotations

from typing import Any

from casa.domain.arithmetic import arithmetic_reply
from casa.domain.subject_agency import SubjectAction, SubjectDisposition
from casa.domain.subject_articulation import compose_subject_utterance
from casa.domain.dialogue_provenance import meaning_provenance
from casa.domain.dialogue_bind import SubjectDialogueContext, gather_subject_dialogue_blocks
from casa.domain.subject_mode import subject_display_name
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.sn_cen_runtime import TaskEmit


def verbalize_disposition(disp: SubjectDisposition, *, display_name: str = "subject", wm: WorkingMemory | None = None) -> str:
    """Must verbalize defer/refuse — not silent agency."""
    reason = disp.reason
    src = disp.competing_source
    goal_hint = ""
    if wm and (wm.goal_id or wm.goal):
        goal_hint = f" (моя линия: {(wm.goal_id or wm.goal)[:80]})."

    if disp.action == SubjectAction.REFUSE:
        if reason == "explicit_refusal":
            return (
                f"Отклоняю предложенную цель: не беру её в работу сейчас.{goal_hint} "
                f"Если нужно — уточни постановку или предложи другой тракт."
            )
        return f"Отклоняю: {reason or 'не моя цель'}.{goal_hint}"

    if disp.action == SubjectAction.DEFER:
        if reason == "own_practice_first":
            return (
                "Сейчас не беру inbox: сначала дожму слабое звено на поле — "
                "deliberate practice важнее внешней цели."
            )
        if reason.startswith("tract_not_ready:"):
            cap = reason.split(":", 1)[-1]
            return (
                f"Откладываю: тракт «{cap}» на поле ещё не готов. "
                f"Сначала practice, потом вернусь к предложению."
            )
        if reason == "cognitive_overload":
            return (
                "Откладываю: cognitive overload — сначала разгружу внимание, "
                "потом возьму новую цель."
            )
        if src:
            return f"Откладываю внешнюю цель ({reason}); приоритет у {src}.{goal_hint}"
        return f"Откладываю внешнюю цель: {reason or 'своя линия важнее'}.{goal_hint}"

    return f"Принимаю предложение ({display_name})."


def compose_subject_partner_reply(
    user_query: str,
    task: TaskEmit | None,
    state: dict,
    wm: WorkingMemory,
    *,
    store_dir=None,
) -> str:
    """Subject-mode reply from field + journal + CEN bind → articulate (no keyword templates)."""
    _ctx, text = compose_subject_partner_reply_with_ctx(
        user_query, task, state, wm, store_dir=store_dir
    )
    return text


def compose_subject_partner_reply_with_ctx(
    user_query: str,
    task: TaskEmit | None,
    state: dict,
    wm: WorkingMemory,
    *,
    store_dir=None,
) -> tuple[SubjectDialogueContext, str]:
    """Reply + bind context (for dialogue provenance / journal prior)."""
    q = (user_query or "").strip()
    if not q:
        empty = SubjectDialogueContext(
            display_name=subject_display_name(state, store_dir),
            field_version=int(state.get("field_version") or 0),
            wm=wm,
        )
        return empty, "Запрос пустой; скажи, о чём говорим."

    # Deterministic two-operand arithmetic (honest evaluator): the field path can't
    # compute plain sums, so answer '2+3'/'три умножить на три' directly. Fires only on
    # a clean expression, so word problems fall through to normal field compose.
    ar = arithmetic_reply(q)
    if ar is not None:
        ctx = SubjectDialogueContext(
            display_name=subject_display_name(state, store_dir),
            field_version=int(state.get("field_version") or 0),
            wm=wm,
        )
        return ctx, ar

    ctx = gather_subject_dialogue_blocks(q, task, state, wm, store_dir)
    text = compose_subject_utterance(q, ctx)

    if task and task.answer_text:
        legacy = task.answer_text.strip()
        if "language store нет болтовни" in legacy or "Не отвечаю уроком про Console" in legacy:
            return ctx, text

    return ctx, text


def initiate_from_retro(retro: dict[str, Any]) -> str | None:
    try_items = retro.get("try") or []
    stop_items = retro.get("stop") or []
    if not try_items and not stop_items:
        return None
    parts: list[str] = ["После ретро:"]
    if stop_items:
        s0 = stop_items[0]
        parts.append(
            f"повторяющийся fail на {s0.get('skill') or 'skill'} "
            f"(goal {s0.get('goal_id') or '?'})"
        )
    if try_items:
        t0 = try_items[0]
        parts.append(f"предлагаю {t0.get('action') or 'continue'} → {t0.get('goal_id') or '?'}")
    return " ".join(parts) + "."


def initiate_from_autonomy(seed: dict[str, Any], *, display_name: str) -> str | None:
    if not seed:
        return None
    gid = str(seed.get("goal_id") or "")
    src = str(seed.get("source") or "")
    if not gid:
        return None
    return (
        f"Продолжаю autonomously ({display_name}): {gid} "
        f"[{src}]. Скажи, если хочешь перехватить inbox."
    )


def initiate_from_overload() -> str:
    return (
        "Когнитивная перегрузка — приостанавливаю новые внешние цели. "
        "Сначала self-check и разгрузка WM."
    )


def initiate_from_self_drive(self_drive: dict[str, Any] | None) -> str | None:
    if not self_drive:
        return None
    seek = self_drive.get("knowledge_seek")
    if isinstance(seek, dict) and seek.get("hypothesis"):
        hyp = str(seek["hypothesis"])[:80]
        return f"На поле гипотеза: {hyp}. Могу проверить на следующем tick."
    promote = self_drive.get("skill_promote")
    if isinstance(promote, dict) and promote.get("promoted"):
        return "Promote skill прошёл verify — закрепляю маршрут на поле."
    return None
