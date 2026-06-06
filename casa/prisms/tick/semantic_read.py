#!/usr/bin/env python3
"""Semantic read v0 — classify partner text, route KB read (field-native, no LLM)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from casa.prisms.control.sn_cen_runtime import _filter_claim_hits, _match_claims, _query_is_dialogue


_CARDINAL_TO_CID = {
    0: "math.num.zero",
    1: "math.num.one",
    2: "math.num.two",
    3: "math.num.three",
    4: "math.num.four",
    5: "math.num.five",
    6: "math.num.six",
    7: "math.num.seven",
    8: "math.num.eight",
    9: "math.num.nine",
    10: "math.num.ten",
}

_OP_GLYPH_TO_CID = {
    "+": "math.op.add",
    "-": "math.op.sub",
    "−": "math.op.sub",
    "×": "math.op.mul",
    "*": "math.op.mul",
    "/": "math.op.div",
    "÷": "math.op.div",
    "=": "math.op.eq",
}

_SOCIAL_SURFACE_TO_CID: tuple[tuple[str, str], ...] = (
    ("привет", "lang.word.привет"),
    ("здравствуй", "lang.word.здравствуйте"),
    ("здравствуйте", "lang.word.здравствуйте"),
    ("добрый день", "ru.dialog.greeting.formal"),
    ("добрый вечер", "ru.dialog.greeting.formal"),
    ("как дела", "ru.dialog.how_are_you"),
    ("спасибо", "lang.word.спасибо"),
    ("до свидания", "ru.dialog.farewell"),
    ("пока", "ru.dialog.farewell"),
)


def _has_cyrillic(text: str) -> bool:
    return bool(re.search(r"[\u0400-\u04FF]", text))


def _has_latin_words(text: str) -> bool:
    return bool(re.search(r"\b[a-z]{3,}\b", text.lower()))


def parse_stick_runs(query: str) -> list[int]:
    return [len(m) for m in re.findall(r"\|+", query)]


def parse_math_ops(query: str) -> list[str]:
    ops: list[str] = []
    for ch in query:
        if ch in _OP_GLYPH_TO_CID and _OP_GLYPH_TO_CID[ch] not in ops:
            ops.append(_OP_GLYPH_TO_CID[ch])
    return ops


@dataclass
class QueryRead:
    intent: str  # social | math | grammar | recall | general
    locales: list[str] = field(default_factory=list)  # ru | en | math_glyph
    stick_counts: list[int] = field(default_factory=list)
    math_ops: list[str] = field(default_factory=list)
    concept_hints: list[str] = field(default_factory=list)
    kb_hits: list[tuple[dict[str, Any], int]] = field(default_factory=list)


def classify_query_intent(query: str) -> str:
    q = (query or "").strip()
    if not q:
        return "general"
    if _query_is_dialogue(q):
        return "social"
    sticks = parse_stick_runs(q)
    ops = parse_math_ops(q)
    ql = q.lower()
    if sticks or ops:
        return "math"
    if any(w in ql for w in ("плюс", "минус", "умнож", "делить", "палоч", "слагаем", "сумм", "разност")):
        return "math"
    if any(
        m in ql
        for m in (
            "согласно",
            "запят",
            "пароним",
            "граммат",
            "орфограф",
            "придаточ",
            "надеть",
            "одеть",
            "по-русски",
            "по русски",
        )
    ):
        return "grammar"
    if any(m in ql for m in ("что такое", "объясни", "расскажи", "what is", "explain")):
        return "recall"
    return "general"


def detect_query_locales(query: str) -> list[str]:
    locs: list[str] = []
    if parse_stick_runs(query) or parse_math_ops(query):
        locs.append("math_glyph")
    if _has_cyrillic(query):
        locs.append("ru")
    if _has_latin_words(query):
        locs.append("en")
    return locs or ["ru"]


def _concept_hints_from_surface(query: str) -> list[str]:
    hints: list[str] = []
    for n in parse_stick_runs(query):
        cid = _CARDINAL_TO_CID.get(n)
        if cid:
            hints.append(cid)
    hints.extend(parse_math_ops(query))
    ql = query.lower()
    for word, cid in (
        ("плюс", "math.op.add"),
        ("минус", "math.op.sub"),
        ("умнож", "math.op.mul"),
        ("дел", "math.op.div"),
        ("слагаем", "math.role.addend"),
        ("сумм", "math.role.sum"),
        ("разност", "math.role.difference"),
        ("палоч", "math.entity.stick"),
        ("кучк", "math.role.heap"),
    ):
        if word in ql:
            hints.append(cid)
    for surface, cid in _SOCIAL_SURFACE_TO_CID:
        if surface in ql:
            hints.append(cid)
    for m in re.findall(r"\b\d+\b", ql):
        n = int(m)
        cid = _CARDINAL_TO_CID.get(n)
        if cid:
            hints.append(cid)
    return list(dict.fromkeys(hints))


def route_kb_read(query: str, bundle: dict[str, Any] | None) -> QueryRead:
    """Parallel read: surface → intent/locale hints → matched KB claims."""
    intent = classify_query_intent(query)
    read = QueryRead(
        intent=intent,
        locales=detect_query_locales(query),
        stick_counts=parse_stick_runs(query),
        math_ops=parse_math_ops(query),
        concept_hints=_concept_hints_from_surface(query),
    )
    if not bundle or not (bundle.get("claims") or []):
        return read

    hits = _filter_claim_hits(query, _match_claims(query, bundle, concept_ids=None))
    by_cid: dict[str, dict[str, Any]] = {
        str(c.get("concept_id") or ""): c for c in (bundle.get("claims") or []) if c.get("concept_id")
    }
    for hint in read.concept_hints:
        if hint in by_cid:
            hits.insert(0, (by_cid[hint], 28))
    for run in re.findall(r"\|+", query):
        for c in bundle.get("claims") or []:
            text = str(c.get("text") or "")
            if run in text and c.get("concept_id"):
                hits.append((c, 18 + len(run)))
    for ch in query:
        if ch in _OP_GLYPH_TO_CID:
            cid = _OP_GLYPH_TO_CID[ch]
            if cid in by_cid:
                hits.insert(0, (by_cid[cid], 26))
    seen: set[str] = set()
    merged: list[tuple[dict[str, Any], int]] = []
    for claim, score in hits:
        cid = str(claim.get("concept_id") or "")
        if cid in seen:
            continue
        seen.add(cid)
        boost = 0
        if cid in read.concept_hints:
            boost += 10
        if intent == "math" and cid.startswith("math."):
            boost += 6
        if intent == "grammar" and ("grammar" in cid or cid.startswith("lang.word.")):
            boost += 4
        if intent == "social" and (
            cid.startswith("ru.dialog.") or cid.startswith("lang.word.")
        ):
            boost += 12
        merged.append((claim, score + boost))
    merged.sort(key=lambda x: x[1], reverse=True)
    read.kb_hits = merged[:6]
    return read
