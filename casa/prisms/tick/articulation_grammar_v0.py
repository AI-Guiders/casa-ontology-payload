#!/usr/bin/env python3
"""Articulation: realize v0 (слоты) + legacy sketch (вставка claims)."""

from __future__ import annotations

from casa._paths import ensure_import_paths

ensure_import_paths()

import re
from typing import Any

from articulation_realize_v0 import compose_answer_text, paste_ratio  # type: ignore


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
    """Console-safe for Windows cp1251 logs; keeps Cyrillic."""
    return (
        text.replace("\u2192", "->")
        .replace("\u2260", "!=")
        .replace("\u2014", "-")
        .replace("\u2026", "...")
    )


def _trim_sentence(text: str, max_len: int = 220) -> str:
    t = _ascii_safe(re.sub(r"\s+", " ", text).strip())
    if len(t) <= max_len:
        return t
    cut = t[: max_len - 1].rsplit(" ", 1)[0]
    return cut + "…"


def compose_answer_text_no_memory(user_query: str, *, reason: str = "weak_match") -> str:
    """Честный отказ: не подставлять C# / случайный claim."""
    q = (user_query or "").strip()
    if reason == "chitchat":
        body = (
            "Это приветствие или свободный разговор — в language store нет болтовни. "
            "Не отвечаю уроком про Console, ReadLine или «сумму двух чисел». "
            "Спроси правило русского, перефраз учебной задачи или «объясни …» по грамматике."
        )
    else:
        body = (
            "По этому запросу нет уверенного фрагмента в grammar/literacy KB "
            "(слишком слабое совпадение слов). Не подменяю ответом про программирование. "
            "Переформулируй: норма, пароним, запятая, «согласно …», перефраз из J0."
        )
    if q:
        return f"Понял: «{q[:120]}{'…' if len(q) > 120 else ''}». {body}"
    return body


def compose_answer_text_sketch(
    user_query: str,
    answer_blocks: tuple[Any, ...] | list[Any],
    *,
    action: str = "answer_from_memory",
) -> str:
    """2–4 предложения на русском: что понял + факты из claims."""
    q = (user_query or "").strip()
    blocks = list(answer_blocks)
    intent = _intent_label(q)

    if not q:
        return "Запрос пустой; уточни, что нужно найти или объяснить."

    parts: list[str] = []
    parts.append(f"Понял: нужно {intent} — «{q[:140]}{'…' if len(q) > 140 else ''}».")

    if not blocks:
        parts.append("В памяти нет подходящего фрагмента; открой KB или переформулируй запрос.")
        return " ".join(parts)

    snippets: list[str] = []
    for b in blocks[:2]:
        t = _block_text(b)
        if len(t) >= 8:
            snippets.append(_trim_sentence(t))

    if snippets:
        joined = " ".join(snippets)
        parts.append(f"По памяти: {joined}")
    else:
        parts.append("По памяти есть раздел, но текст claim слишком короткий для пересказа.")

    cids = [_block_cid(b) for b in blocks[:3]]
    if any(c.startswith("ru.dialog.") or c.startswith("ru.lang.word.") for c in cids):
        parts.append("Это разговорный слой (dialogue KB), не урок программирования.")
    elif any("ru.grammar" in c or "language-rules" in c for c in cids):
        parts.append("Опираюсь на норму русского письма (grammar KB).")
    elif any("literacy" in c for c in cids):
        parts.append("Это учебная формулировка из literacy KB (как читать запрос).")
    elif action == "open_kb":
        parts.append("Могу открыть указанный раздел в KB для деталей.")

    text = _ascii_safe(" ".join(parts))
    if not text.endswith((".", "!", "?")):
        text += "."
    return text
