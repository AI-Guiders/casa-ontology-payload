#!/usr/bin/env python3
"""Subject articulation — realize from field/journal atoms, not language-lab templates."""

from __future__ import annotations

import re
from typing import Any

from casa.domain.subject_dialogue_bind import SubjectDialogueContext, _social_query
from casa.prisms.tick.articulation_realize import (
    GrammarAtom,
    UtterancePlan,
    _block_cid,
    _block_text,
    _extract_grammar_atom,
    _realize_compare,
    _realize_explain,
    _realize_check_norm,
)


def _trim(text: str, max_len: int = 200) -> str:
    t = re.sub(r"\s+", " ", str(text or "").strip())
    if len(t) <= max_len:
        return t
    cut = t[: max_len - 1].rsplit(" ", 1)[0]
    return cut + "…"


def _blocks_with_prefix(ctx: SubjectDialogueContext, prefix: str) -> list[dict[str, Any]]:
    return [b for b in ctx.blocks if str(b.get("concept_id") or "").startswith(prefix)]


def _has_kb_grammar(ctx: SubjectDialogueContext) -> bool:
    for b in ctx.blocks:
        cid = str(b.get("concept_id") or "")
        if b.get("source") == "kb" and ("grammar" in cid or cid.startswith("ru.grammar.")):
            return True
    return False


def _kb_social_opening(ctx: SubjectDialogueContext, act: str) -> str | None:
    want = {
        "greeting": ("ru.dialog.greeting", "lang.word.привет", "ru.dialog.greeting.formal"),
        "how_are_you": ("ru.dialog.how_are_you",),
        "intro": ("ru.dialog.self", "ru.dialog.capabilities"),
    }.get(act, ())
    for b in ctx.blocks:
        if str(b.get("source")) != "kb":
            continue
        cid = str(b.get("concept_id") or "")
        if not any(cid.startswith(p) for p in want):
            continue
        text = _block_text(b)
        quoted = re.findall(r"«([^»]{1,40})»", text)
        if quoted and act == "greeting":
            return f"{quoted[0].capitalize()}."
        first = re.split(r"[.;]", text, maxsplit=1)[0].strip()
        if first:
            return first if first.endswith((".", "!", "?")) else first + "."
    return None


def _realize_math(ctx: SubjectDialogueContext, query: str) -> str | None:
    top = ctx.blocks[0] if ctx.blocks else {}
    if top.get("source") == "journal" and str(top.get("section") or "") == "confirmed":
        cid = str(top.get("concept_id") or "")
        text = _trim(_block_text(top), 120)
        if text:
            return f"На поле: {text} ({cid})."

    math_blocks = _blocks_with_prefix(ctx, "math.")
    lang_blocks = _blocks_with_prefix(ctx, "lang.word.")
    if not math_blocks and not ctx.concept_hints:
        return None

    parts: list[str] = ["На поле (math):"]
    sticks = ctx.concept_hints or []
    stick_nums = [h for h in sticks if h.startswith("math.num.")]
    op_ids = [h for h in sticks if h.startswith("math.op.")]

    for cid in stick_nums[:2]:
        for b in math_blocks:
            if b.get("concept_id") == cid:
                parts.append(_trim(_block_text(b), 80))
                break

    for b in math_blocks:
        cid = str(b.get("concept_id") or "")
        if cid in op_ids:
            parts.append(_trim(_block_text(b), 90))

    for b in lang_blocks[:2]:
        if b.get("source") == "kb":
            parts.append(_trim(_block_text(b), 70))

    if len(parts) <= 1:
        for b in math_blocks[:3]:
            parts.append(_trim(_block_text(b), 90))

    if ctx.query_locales:
        parts.append(f"локали: {', '.join(ctx.query_locales)}.")
    return " ".join(parts)


def _journal_excerpt(ctx: SubjectDialogueContext, *, max_sents: int = 2) -> str | None:
    journals = _blocks_with_prefix(ctx, "agent.self.journal.")
    if not journals:
        return None
    text = _block_text(journals[0])
    if not text:
        return None
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if not sents:
        return _trim(text, 200)
    return " ".join(sents[:max_sents])


def _stance_label(ctx: SubjectDialogueContext) -> str:
    if ctx.stance == "confident":
        return "опираюсь на поле и journal"
    if ctx.stance == "partial":
        return "уверен частично"
    return "bind слабый — не выдумаю"


def _grammar_body(plan: UtterancePlan, query: str, ctx: SubjectDialogueContext) -> str | None:
    kb_grammar = [
        b
        for b in ctx.blocks
        if b.get("source") in ("kb", "cen") and "grammar" in str(b.get("concept_id") or "")
    ]
    cen_grammar = [b for b in ctx.blocks if b.get("source") == "cen" and "grammar" in str(b.get("concept_id") or "")]
    if cen_grammar:
        atom = _extract_grammar_atom(_block_text(cen_grammar[0]))
        if atom:
            return f"По полю: {atom.headline}"
        return f"По полю: {_trim(_block_text(cen_grammar[0]), 180)}"
    if kb_grammar:
        return f"По KB: {_trim(_block_text(kb_grammar[0]), 180)}"
    if not _has_kb_grammar(ctx):
        return None
    if plan.intent == "проверка нормы":
        chk = _realize_check_norm(query)
        if chk:
            return f"Проверка: {chk}"
    if plan.intent == "объяснение":
        expl = _realize_explain(query)
        if expl:
            return f"Коротко: {expl}"
    cmp = _realize_compare(query, plan.atoms)
    if cmp:
        if plan.intent == "проверка нормы":
            return f"Проверка: {cmp}"
        if " или " in query.lower():
            return f"Различие: {cmp}"
        return cmp
    if plan.atoms:
        parts: list[str] = []
        for atom in plan.atoms[:2]:
            if atom.detail:
                parts.append(f"{atom.headline} — {atom.detail}")
            else:
                parts.append(atom.headline[:96])
        body = " ".join(parts)
        if plan.intent == "объяснение":
            return f"Коротко по норме: {body}"
        return f"По вопросу: {body}"
    return None


def _atoms_from_blocks(ctx: SubjectDialogueContext, query: str) -> list[GrammarAtom]:
    atoms: list[GrammarAtom] = []
    for b in ctx.blocks[:6]:
        cid = _block_cid(b)
        text = _block_text(b)
        if cid.startswith("ru.grammar.") or "→" in text or "Правильно:" in text:
            atom = _extract_grammar_atom(text)
            if atom:
                atoms.append(atom)
        elif cid.startswith("agent.self.journal.") and len(atoms) < 3:
            head = _trim(text, 120)
            if head:
                atoms.append(GrammarAtom(kind="rule", headline=head))
    return atoms


def _realize_social(plan: UtterancePlan, query: str, ctx: SubjectDialogueContext) -> str:
    parts: list[str] = []
    act = plan.act or _social_query(query) or "dialogue"

    opening = _kb_social_opening(ctx, act)
    if opening:
        parts.append(opening)
    elif act == "greeting":
        parts.append("Привет.")
    elif act == "how_are_you":
        parts.append("Спасибо, что спросил.")

    identity = _journal_excerpt(ctx, max_sents=2 if act in ("greeting", "intro") else 1)
    if identity:
        parts.append(identity if identity.endswith((".", "!", "?")) else identity + ".")
    else:
        parts.append(f"Я {ctx.display_name} — субъект на поле CASA.")

    snap = _blocks_with_prefix(ctx, "subject.field.snapshot")
    if snap and act == "how_are_you":
        parts.append(_trim(_block_text(snap[0]), 100))

    cap = _blocks_with_prefix(ctx, "subject.self.capability")
    if cap and act == "intro":
        parts.append(_trim(_block_text(cap[0]), 140))

    goal = (ctx.wm.goal_id or ctx.wm.goal or "").strip()
    if goal and act in ("greeting", "intro"):
        parts.append(f"Сейчас в фокусе: {goal}.")

    if act == "how_are_you":
        parts.append("Сам настроение не чувствую — живу тиками на поле; линия диалога для меня важна.")
        parts.append("О чём поговорим?")
    elif act == "intro":
        parts.append("Позиция из store и journal, не облачный LLM без provenance.")

    body = " ".join(p for p in parts if p)
    return body


def _realize_recall(plan: UtterancePlan, query: str, ctx: SubjectDialogueContext) -> str | None:
    confirmed = [b for b in ctx.blocks if str(b.get("section") or "") == "confirmed"]
    if confirmed:
        return _trim(_block_text(confirmed[0]), 220)
    for b in ctx.blocks:
        if b.get("source") != "journal":
            continue
        text = _block_text(b)
        if text and any(tok in text.lower() for tok in ("купил", "сказал", "ушёл", "ушел", "вернулся")):
            return _trim(text, 220)
    lang_hits = [b for b in ctx.blocks if str(b.get("concept_id") or "").startswith("lang.word.")]
    if lang_hits:
        return _trim(_block_text(lang_hits[0]), 160)
    return None


def _realize_soft_miss(plan: UtterancePlan, query: str, ctx: SubjectDialogueContext) -> str:
    if ctx.query_intent == "math":
        math = _realize_math(ctx, query)
        if math:
            return math
    grammar = _grammar_body(plan, query, ctx)
    if grammar:
        return grammar
    if ctx.query_intent == "grammar":
        return (
            f"Слышу: «{_trim(query, 100)}». На поле нет grammar claim в KB — "
            f"не подменяю зашитым правилом; нужен ingest или practice."
        )
    journals = _blocks_with_prefix(ctx, "agent.self.journal.")
    if journals:
        return _trim(_block_text(journals[0]), 220)
    qshort = _trim(query, 120)
    return (
        f"Слышу: «{qshort}». На поле пока нет уверенного bind — "
        f"могу уточнить тракт или сказать, что нужно ingest/practice."
    )


def realize_subject(plan: UtterancePlan, user_query: str, ctx: SubjectDialogueContext) -> str:
    """Compose subject reply from bound atoms — no language-lab chitchat templates."""
    q = (user_query or "").strip()
    act = plan.act or "dialogue"

    if not plan.atoms:
        plan.atoms.extend(_atoms_from_blocks(ctx, q))

    if ctx.query_intent == "recall":
        body = _realize_recall(plan, q, ctx) or _realize_soft_miss(plan, q, ctx)
    elif act in ("greeting", "how_are_you", "intro"):
        body = _realize_social(plan, q, ctx)
    elif ctx.query_intent == "grammar":
        body = _grammar_body(plan, q, ctx) or _realize_soft_miss(plan, q, ctx)
    elif ctx.query_intent == "math" or act in ("explain_rule", "compare_forms", "dialogue"):
        body = _realize_math(ctx, q) or _grammar_body(plan, q, ctx) or _realize_soft_miss(plan, q, ctx)
    elif act in ("phrase_call_mama", "phrase_help"):
        body = _grammar_body(plan, q, ctx) or _realize_social(plan, q, ctx)
    elif act == "soft_miss":
        body = _realize_soft_miss(plan, q, ctx)
    else:
        body = _realize_soft_miss(plan, q, ctx)

    sources = ", ".join(ctx.source_tags[:5]) or "field"
    stance = _stance_label(ctx)
    return f"{body} ({stance}; {sources}, не paste claim)."


def compose_subject_utterance(
    user_query: str,
    ctx: SubjectDialogueContext,
    plan: UtterancePlan | None = None,
) -> str:
    from casa.domain.subject_dialogue_bind import build_subject_plan

    p = plan or build_subject_plan(user_query, ctx)
    return realize_subject(p, user_query, ctx)
