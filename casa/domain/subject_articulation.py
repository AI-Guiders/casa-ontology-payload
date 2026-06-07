#!/usr/bin/env python3
"""Subject articulation — phrase compose from field slots, not claim paste."""

from __future__ import annotations

import re
from typing import Any

from casa.domain.dialogue_bind import SubjectDialogueContext
from casa.prisms.tick.articulation_realize import (
    GrammarAtom,
    UtterancePlan,
    _block_cid,
    _block_text,
    _extract_grammar_atom,
)
from casa.prisms.tick.phrase_compose import compose_subject_phrase

_JOURNAL_BOOTSTRAP_MARKERS = (
    "это мой журнал",
    "я — нейманн",
    "я - нейманн",
)


def _trim(text: str, max_len: int = 200) -> str:
    t = re.sub(r"\s+", " ", str(text or "").strip())
    if len(t) <= max_len:
        return t
    cut = t[: max_len - 1].rsplit(" ", 1)[0]
    return cut + "…"


def _is_journal_bootstrap_text(text: str) -> bool:
    tl = str(text or "").lower()
    return any(m in tl for m in _JOURNAL_BOOTSTRAP_MARKERS)


def _blocks_with_prefix(ctx: SubjectDialogueContext, prefix: str) -> list[dict[str, Any]]:
    return [b for b in ctx.blocks if str(b.get("concept_id") or "").startswith(prefix)]


def _compose_blocks(ctx: SubjectDialogueContext, query: str) -> list[dict[str, Any]]:
    """Blocks eligible for phrase compose — no meta, no bootstrap; echo lemmas only on social."""
    ql = query.lower()
    out: list[dict[str, Any]] = []
    for b in ctx.blocks:
        cid = str(b.get("concept_id") or "")
        if cid.startswith("subject."):
            continue
        text = _block_text(b)
        if b.get("source") == "journal" and _is_journal_bootstrap_text(text):
            continue
        if cid.startswith("lang.word.") and ctx.query_intent not in ("explain", "grammar"):
            lemma = cid.rsplit(".", 1)[-1].lower()
            if lemma and lemma in ql:
                continue
        out.append(b)
    return out


def _realize_math(ctx: SubjectDialogueContext, query: str) -> str | None:
    math_blocks = _blocks_with_prefix(ctx, "math.")
    if not math_blocks and not ctx.concept_hints:
        return None
    parts: list[str] = ["На поле (math):"]
    for b in math_blocks[:3]:
        parts.append(_trim(_block_text(b), 90))
    return " ".join(parts) if len(parts) > 1 else None


def _atoms_from_blocks(ctx: SubjectDialogueContext) -> list[GrammarAtom]:
    atoms: list[GrammarAtom] = []
    for b in ctx.blocks:
        cid = _block_cid(b)
        text = _block_text(b)
        if cid.startswith("ru.grammar.") or "→" in text or "Правильно:" in text:
            atom = _extract_grammar_atom(text)
            if atom:
                atoms.append(atom)
    return atoms


def realize_subject(plan: UtterancePlan, user_query: str, ctx: SubjectDialogueContext) -> str:
    """Subject builds its own phrase from bound slots/lexemes — no fixed reply strings."""
    q = (user_query or "").strip()

    if not plan.atoms:
        plan.atoms.extend(_atoms_from_blocks(ctx))

    blocks = _compose_blocks(ctx, q)
    body: str | None = None

    if ctx.query_intent == "math":
        body = _realize_math(ctx, q)

    if not body:
        body = compose_subject_phrase(
            plan,
            q,
            blocks=blocks,
            query_intent=ctx.query_intent,
            stance=ctx.stance,
            agent_tract_profile=ctx.agent_tract_profile,
        )

    return (body or "").strip()


def compose_subject_utterance(
    user_query: str,
    ctx: SubjectDialogueContext,
    plan: UtterancePlan | None = None,
) -> str:
    from casa.domain.dialogue_bind import build_subject_plan

    p = plan or build_subject_plan(user_query, ctx)
    return realize_subject(p, user_query, ctx)
