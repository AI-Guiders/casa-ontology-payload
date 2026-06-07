#!/usr/bin/env python3
"""Register-shift rewrite helpers for passage+question turns."""

from __future__ import annotations

import re
from typing import Any

from casa.prisms.tick.discourse.policy import BlockDiscoursePolicy
from casa.prisms.tick.discourse.slots import BlockSlots


def passage_fact_anchors(passage: str) -> list[str]:
    found: list[str] = []
    for m in re.finditer(r"\d{1,2}:\d{2}", passage):
        found.append(m.group(0))
    for m in re.finditer(
        r"\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)",
        passage,
        flags=re.IGNORECASE,
    ):
        found.append(m.group(0))
    for m in re.finditer(r"№\s*\d+", passage):
        found.append(m.group(0).replace(" ", ""))
    for m in re.finditer(
        r"(?:на|в)\s+(понедельник\w*|вторник\w*|сред\w*|четверг\w*|пятниц\w*|суббот\w*|воскресен\w*)",
        passage,
        flags=re.IGNORECASE,
    ):
        found.append(m.group(1))
    return found


def anchors_present(text: str, anchors: list[str]) -> bool:
    tl = text.lower()
    return all(a.lower() in tl for a in anchors if a)


def rewrite_from_props(blocks: list[dict[str, Any]], question: str) -> str | None:
    event_block: dict[str, Any] | None = None
    informal = False
    for b in blocks:
        cid = str(b.get("concept_id") or "")
        if cid.startswith("ru.prop.event."):
            event_block = b
        if cid == "ru.prop.constraint.shift_register":
            informal = True
    if not event_block:
        return None
    slots = BlockSlots.read(event_block)
    ql = question.lower()
    parts: list[str] = []
    if informal or slots.get("register") == "informal":
        if "родител" in ql or slots.get("addressee") == "родители":
            parts.append("Родители,")
        elif "чат" in ql:
            parts.append("Всем в чате:")
    body = slots.get("clause_1") or ""
    if body:
        parts.append(body)
    if not parts:
        return None
    line = " ".join(parts)
    return line[0].upper() + line[1:] + "."


def rewrite_fact_assembly(passage: str, question: str) -> str | None:
    anchors = passage_fact_anchors(passage)
    if not anchors and "собран" not in passage.lower():
        return None
    ql = question.lower()
    parts: list[str] = []
    if "родител" in ql:
        parts.append("Родители,")
    elif "чат" in ql:
        parts.append("Всем в чате:")
    if "собран" in passage.lower():
        parts.append("родительское собрание перенесли")
    weekday = re.search(
        r"(?:на|в)\s+(понедельник\w*|вторник\w*|сред\w*|четверг\w*|пятниц\w*|суббот\w*|воскресен\w*)",
        passage,
        flags=re.IGNORECASE,
    )
    if weekday:
        parts.append(f"на {weekday.group(1).lower()}")
    loc = re.search(r"в\s+актовом\s+зале\s+школы\s*№\s*\d+", passage, flags=re.IGNORECASE)
    if loc:
        parts.append(loc.group(0).replace("актовом зале", "актовый зал"))
    body = " ".join(parts).lower()
    for anchor in anchors:
        low = anchor.lower()
        if low in body:
            continue
        if re.match(r"\d{1,2}:\d{2}", anchor):
            parts.append(f"в {anchor}")
        elif re.match(r"\d{1,2}\s+", anchor):
            parts.append(f"на {anchor}")
        else:
            parts.append(anchor)
    if not parts:
        return None
    line = " ".join(parts)
    return line[0].upper() + line[1:] + "."
