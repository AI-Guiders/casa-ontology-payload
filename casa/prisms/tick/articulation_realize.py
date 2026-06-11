#!/usr/bin/env python3
"""Articulation realize v0: utterance from slots + lexemes, not claim paste."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import re
from typing import Any

from casa.prisms.tick.articulation.model import GrammarAtom, UtterancePlan


def _intent_label(query: str) -> str:
    q = query.lower()
    if any(x in q for x in ("объясни", "расскажи", "что такое", "чем отличается", "простыми словами")):
        return "объяснение"
    if any(x in q for x in ("верно", "правильно", "проверь", "можно ли", "ошибка", "ошибочно")):
        return "проверка нормы"
    if any(x in q for x in ("напиши", "сделай", "создай", "составь")):
        return "выполнение задачи"
    if any(x in q for x in ("найди", "покажи", "где в")):
        return "поиск в памяти"
    return "ответ по запросу"


def _block_text(block: Any) -> str:
    if hasattr(block, "text"):
        return str(block.text or "").strip()
    if isinstance(block, dict):
        return str(block.get("text") or "").strip()
    return ""


def _block_cid(block: Any) -> str:
    if hasattr(block, "concept_id"):
        return str(block.concept_id or "")
    if isinstance(block, dict):
        return str(block.get("concept_id") or "")
    return ""


def _ascii_safe(text: str) -> str:
    return (
        text.replace("\u2192", "->")
        .replace("\u2260", "!=")
        .replace("\u2014", "-")
        .replace("\u2026", "...")
    )


def _lemma_from_word_cid(cid: str, text: str) -> str | None:
    if not cid.startswith("ru.lang.word."):
        return None
    quoted = re.findall(r"«([^»]{1,40})»", text)
    if quoted:
        return quoted[0].strip()
    tail = cid.rsplit(".", 1)[-1]
    if tail in ("ya", "ty", "mama", "papa"):
        return {"ya": "я", "ty": "ты", "mama": "мама", "papa": "папа"}.get(tail, tail)
    return None


_META_MARKERS = ("doc_id:", "kb-russian-literacy", "цель:", "следующий kb", "cen читать")


def _is_meta_claim(text: str) -> bool:
    tl = text.lower()
    return any(m in tl for m in _META_MARKERS)


def _block_relevance(query: str, text: str, cid: str) -> int:
    score = 0
    if cid.startswith("ru.grammar."):
        score += 12
    if _is_meta_claim(text):
        score -= 80
    ql = query.lower()
    for token in re.findall(r"[а-яёa-z0-9-]{4,}", ql, re.IGNORECASE):
        if token in text.lower():
            score += 4
    if "по русски" in ql or "по-русски" in ql:
        if "по-русски" in text.lower() or "по русски" in text.lower():
            score += 25
    if "запят" in ql and "запят" in text.lower():
        score += 8
    if " или " in ql and (" или " in text.lower() or "→" in text or "->" in text):
        score += 6
    return score


def _extract_grammar_atom(text: str) -> GrammarAtom | None:
    t = _ascii_safe(re.sub(r"\s+", " ", text).strip())
    if len(t) < 10 or _is_meta_claim(t):
        return None
    m = re.search(r"Правильно:\s*([^.;]+)", t, re.IGNORECASE)
    if m:
        head = m.group(1).strip().rstrip(".")
        return GrammarAtom(kind="rule", headline=head[:100])
    m = re.search(r"верно только\s+([^.;]+)", t, re.IGNORECASE)
    if m:
        return GrammarAtom(kind="compare", headline=m.group(1).strip()[:100])
    m = re.search(r"([^→]+)\s*→\s*([^.;]+)", t)
    if m:
        return GrammarAtom(
            kind="compare",
            headline=m.group(2).strip()[:80],
            detail=f"ошибка: {m.group(1).strip()[:40]}",
        )
    if " — " in t and not t.startswith("Надеть"):
        head, detail = t.split(" — ", 1)
        return GrammarAtom(
            kind="rule",
            headline=head.strip()[:72],
            detail=detail.strip()[:88],
        )
    first = re.split(r"[.;]", t, maxsplit=1)[0].strip()
    if 12 <= len(first) <= 120:
        return GrammarAtom(kind="rule", headline=first)
    return None


def _realize_explain(query: str) -> str | None:
    ql = query.lower()
    if "запят" in ql and "что" in ql:
        return (
            "В придаточном с «что» ставят запятую перед союзом: "
            "«Я знаю, что он придёт»."
        )
    if "пароним" in ql and ("надел" in ql or "одеть" in ql):
        return (
            "«Надеть» — на себя вещь; «одеть» — на другого. "
            "Это частые паронимы в бытовой речи."
        )
    return None


def _realize_compare(query: str, atoms: list[GrammarAtom]) -> str | None:
    ql = query.lower()
    if "согласно" in ql:
        return (
            "Норма — дательный падеж: согласно приказу, договору, закону. "
            "«Согласно приказа» в официальном стиле не пишут."
        )
    if "одеть" in ql and "надеть" in ql:
        return (
            "«Надеть» — на себя или на кого-то вещь (надел пальто, очки). "
            "«Одеть» — облечь другого (одеть ребёнка). С «пальто» чаще «надеть пальто»."
        )
    if "течени" in ql:
        return (
            "В значении «в процессе времени» пишут слитно: в течение часа, в течение дня. "
            "«В течении» — ошибка (путают с «в течение чего-то»)."
        )
    if "по русски" in ql or "по-русски" in ql:
        return (
            "Верно только с дефисом: по-русски, по-английски. "
            "Раздельное «по русски» — нарушение нормы."
        )
    if "также" in ql and "так же" in ql:
        return (
            "«Также» слитно — «и ещё». «Так же» раздельно — «тем же образом». "
            "В начале фразы чаще «Также, …»."
        )
    if atoms and atoms[0].kind == "compare":
        return atoms[0].headline
    return None


def _act_from_cid(cid: str) -> str | None:
    if cid.startswith("ru.dialog.greeting"):
        return "greeting"
    if cid.startswith("ru.dialog.how_are_you"):
        return "how_are_you"
    if cid.startswith("ru.dialog.self") or cid.startswith("ru.dialog.capabilities"):
        return "intro"
    if cid.startswith("ru.dialog.call_mama"):
        return "phrase_call_mama"
    if cid.startswith("ru.dialog.phrase_help"):
        return "phrase_help"
    if cid.startswith("ru.dialog.soft_miss"):
        return "soft_miss"
    if cid.startswith("ru.dialog.thanks"):
        return "thanks"
    if cid.startswith("ru.dialog.farewell"):
        return "farewell"
    return None


# Partner dialogue uses compose_subject_utterance (bind winners) — never these realize templates.
_PARTNER_DIALOGUE_ACTS = frozenset(
    {
        "greeting",
        "how_are_you",
        "intro",
        "intro_self",
        "thanks",
        "farewell",
        "mirror_ack",
        "ask_thought",
        "thread_turn",
        "dialogue",
        "phrase_call_mama",
        "phrase_help",
    }
)


def build_plan(
    user_query: str,
    answer_blocks: tuple[Any, ...] | list[Any],
) -> UtterancePlan:
    from casa.prisms.tick.semantic_read import passage_focus_query

    q = (user_query or "").strip()
    intent = _intent_label(passage_focus_query(q))
    blocks = list(answer_blocks)
    cids = [_block_cid(b) for b in blocks if _block_cid(b)]
    lexemes: dict[str, str] = {}
    atoms: list[GrammarAtom] = []
    act = ""

    ql = passage_focus_query(q).lower()
    social_act = None
    try:
        from casa.prisms.tick.partner_speech_act import resolve_partner_speech_act

        social_act = resolve_partner_speech_act(q, blocks=blocks)
    except ImportError:
        social_act = None
    if social_act:
        act = social_act
    elif "мама" in ql or "папа" in ql:
        if any(x in ql for x in ("позвонить", "набрать", "сказать", "сформулировать", "написать")):
            act = "phrase_call_mama"
        else:
            lexemes.setdefault("addressee", "мама")

    ranked = sorted(
        blocks,
        key=lambda b: _block_relevance(q, _block_text(b), _block_cid(b)),
        reverse=True,
    )
    for b in ranked[:4]:
        cid = _block_cid(b)
        text = _block_text(b)
        if not cid:
            continue
        mapped = _act_from_cid(cid)
        if mapped and not act and mapped not in _PARTNER_DIALOGUE_ACTS:
            act = mapped
        lemma = _lemma_from_word_cid(cid, text)
        if lemma:
            if "mama" in cid or lemma.lower() == "мама":
                lexemes["addressee"] = lemma
            elif "ty" in cid or lemma.lower() == "ты":
                lexemes["addressee_you"] = lemma
            elif "ya" in cid or lemma.lower() == "я":
                lexemes["speaker"] = lemma
            else:
                lexemes.setdefault("term", lemma)
        if (cid.startswith("ru.grammar.") or "→" in text or "Правильно:" in text) and len(atoms) < 2:
            atom = _extract_grammar_atom(text)
            if atom:
                atoms.append(atom)

    if not act:
        if cids and all(c.startswith("ru.dialog.") or c.startswith("ru.lang.word.") for c in cids[:2]):
            act = "soft_miss"
        elif " или " in ql or " vs " in ql:
            act = "compare_forms"
        elif intent == "проверка нормы":
            act = "explain_rule"
        elif intent == "объяснение":
            act = "explain_rule"
        elif atoms:
            act = "compare_forms" if " или " in ql else "explain_rule"
        elif cids and cids[0].startswith("ru.grammar."):
            act = "explain_rule"
        else:
            act = "soft_miss"

    if act == "phrase_call_mama" and "addressee" not in lexemes:
        lexemes["addressee"] = "мама"

    return UtterancePlan(act=act, intent=intent, lexemes=lexemes, atoms=atoms, concept_ids=cids)


def _realize_check_norm(query: str) -> str | None:
    ql = query.lower()
    if "знаю" in ql and " что " in ql:
        return (
            "Нужна запятая перед придаточным: «Я знаю, что он придёт». "
            "Без запятой — ошибка."
        )
    if "согласно" in ql and ("указа" in ql or "приказа" in ql):
        return (
            "С «согласно» нужен дательный: согласно указу, приказу. "
            "«Согласно указа/приказа» — неверно."
        )
    return None


def realize(plan: UtterancePlan, user_query: str) -> str:
    act = plan.act
    L = plan.lexemes

    if plan.intent == "проверка нормы":
        chk = _realize_check_norm(user_query)
        if chk:
            return f"Проверка: {chk}"

    if act in _PARTNER_DIALOGUE_ACTS:
        return ""

    if act == "phrase_call_mama":
        who = L.get("addressee", "мама")
        who_dat = "маме" if who.lower() == "мама" else who
        return (
            f"Можно написать {who_dat}: «{who.capitalize()}, привет! Вечером наберу — "
            f"хочу поговорить.» Или короче: «Добрый вечер, {who}, как у тебя дела?»"
        )
    if act == "soft_miss":
        cmp = _realize_compare(user_query, plan.atoms)
        if cmp:
            return cmp
        expl = _realize_explain(user_query)
        if expl:
            return expl
        return (
            "Точного куска в памяти нет, но могу помочь иначе: правило русского, "
            "перефраз учебной задачи или короткая бытовая формулировка."
        )

    if act in ("explain_rule", "compare_forms", "dialogue"):
        if plan.intent == "объяснение":
            expl = _realize_explain(user_query)
            if expl:
                return f"Коротко: {expl}"
        cmp = _realize_compare(user_query, plan.atoms)
        if cmp:
            if plan.intent == "объяснение":
                return f"Коротко: {cmp}"
            if plan.intent == "проверка нормы":
                return f"Проверка: {cmp}"
            if " или " in user_query.lower():
                return f"Различие: {cmp}"
            return cmp
        if plan.atoms:
            parts: list[str] = []
            for atom in plan.atoms[:2]:
                if atom.kind == "rule" and atom.detail:
                    parts.append(f"{atom.headline} — {atom.detail}")
                else:
                    parts.append(atom.headline[:96])
            body = " ".join(parts)
            if plan.intent == "объяснение":
                return f"Коротко по норме: {body}"
            if plan.intent == "проверка нормы":
                return f"Проверка: {body}"
            if " или " in user_query.lower():
                return f"Различие: {body}"
            return f"По вопросу: {body}"

    if L.get("term"):
        return f"Слово «{L['term']}» есть в памяти; спроси, как его употребить в фразе."

    return (
        "Пока не собрал план ответа из понятий; переформулируй запрос "
        "или уточни правило."
    )


def compose_answer_text(
    user_query: str,
    answer_blocks: tuple[Any, ...] | list[Any],
    *,
    action: str = "answer_from_memory",
) -> str:
    """Hot path: plan + realize (no claim paste)."""
    q = (user_query or "").strip()
    if not q:
        return "Запрос пустой; уточни, что нужно найти или объяснить."

    plan = build_plan(q, answer_blocks)
    body = realize(plan, q)
    short_q = q if q and len(q) <= 90 else ""
    opener = f"Понял: {plan.intent}."
    if short_q:
        opener = f"Понял: {plan.intent} — «{short_q}»."

    tail = ""
    if plan.act.startswith("phrase_") or plan.act in ("greeting", "how_are_you", "intro"):
        tail = " (dialogue)"
    elif plan.atoms or plan.act in ("explain_rule", "compare_forms"):
        tail = " (grammar)"

    text = _ascii_safe(f"{opener} {body}{tail}.")
    return text


def paste_ratio(answer_text: str, answer_blocks: list[Any]) -> float:
    """Доля символов ответа, совпадающая с подстрокой claim (bench)."""
    if not answer_text:
        return 0.0
    at = answer_text.lower()
    pasted = 0
    for b in answer_blocks:
        t = _block_text(b)
        if len(t) < 24:
            continue
        chunk = t.lower()[: min(80, len(t))]
        if chunk in at:
            pasted += len(chunk)
    return min(1.0, pasted / max(len(at), 1))
