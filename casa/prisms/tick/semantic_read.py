#!/usr/bin/env python3
"""Semantic read — tract competition intent + KB route (ADR-0052)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from casa.prisms.control.sn_cen_runtime import _filter_claim_hits, _match_claims
from casa.prisms.tick.tract import compete_tract_intent, parse_math_ops, parse_stick_runs


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


@dataclass
class QueryRead:
    intent: str  # social | math | grammar | recall | general
    locales: list[str] = field(default_factory=list)  # ru | en | math_glyph
    stick_counts: list[int] = field(default_factory=list)
    math_ops: list[str] = field(default_factory=list)
    concept_hints: list[str] = field(default_factory=list)
    kb_hits: list[tuple[dict[str, Any], int]] = field(default_factory=list)
    tract_ranked: list[Any] = field(default_factory=list)


def has_passage_context(query: str) -> bool:
    from casa.prisms.tick.passage import has_passage_context as _has

    return _has(query)


def passage_focus_query(query: str) -> str:
    """Passage + question turn: classify/act on the question line, not quoted dialogue in passage."""
    q = (query or "").strip()
    if not q:
        return q
    parts = [p.strip() for p in re.split(r"\n\s*\n", q) if p.strip()]
    if len(parts) >= 2:
        return parts[-1]
    return q


def classify_query_intent(
    query: str,
    bundle: dict[str, Any] | None = None,
    *,
    store_dir: Any | None = None,
    state: dict[str, Any] | None = None,
) -> str:
    """Intent = winning tract (ADR-0052). Bundle optional for tests without store."""
    intent, _ = compete_tract_intent(query, bundle, store_dir=store_dir, state=state)
    return intent


def _has_inline_check_text(raw: str) -> bool:
    """Partner attached the snippet to check (quotes or clause after colon)."""
    q = (raw or "").strip()
    if "«" in q and "»" in q and re.search(r"«[^»]{4,}»", q):
        return True
    m = re.search(r":\s*(\S.+\S)", q)
    if m:
        words = re.findall(r"[\w\u0400-\u04FF]+", m.group(1), flags=re.UNICODE)
        if len(words) >= 3:
            return True
    return False


def _geometry_honest_boosts(
    query: str,
    prelim: list[tuple[dict[str, Any], int]],
) -> dict[str, int]:
    """Clarify vs partial only when KB already lit honest atoms — not every short/passage turn."""
    raw = (query or "").strip()
    by_cid = {str(c.get("concept_id") or ""): s for c, s in prelim}
    clarify = max((s for cid, s in by_cid.items() if cid.startswith("ru.dialog.clarify.")), default=0)
    partial = max((s for cid, s in by_cid.items() if cid.startswith("ru.dialog.honest.partial")), default=0)
    if clarify <= 0 and partial <= 0:
        return {}
    boosts: dict[str, int] = {}
    if has_passage_context(raw) and partial > 0:
        boosts["ru.dialog.honest.partial_scope"] = 16
        boosts["ru.dialog.clarify.missing_text"] = -14
    elif not has_passage_context(raw) and clarify > 0:
        words = re.findall(r"[\w\u0400-\u04FF]+", raw, flags=re.UNICODE)
        if _has_inline_check_text(raw):
            boosts["ru.dialog.clarify.missing_text"] = -20
        elif len(words) <= 20:
            boosts["ru.dialog.clarify.missing_text"] = 10
    return boosts


def _intent_boost_for_claim(
    cid: str,
    *,
    intent: str,
    query: str,
    concept_hints: list[str],
) -> int:
    boost = 0
    if cid in concept_hints:
        boost += 10
    if intent == "math" and cid.startswith("math."):
        boost += 6
    if intent == "explain":
        if cid.startswith("ru.dialog.explain"):
            boost += 22
        elif cid.startswith("lang.word."):
            boost += 16
        elif cid.startswith("ru.dialog."):
            boost -= 12
    if intent == "social":
        if cid.startswith("ru.dialog."):
            boost += 18
        elif cid.startswith("lang.word."):
            boost += 8
            surface = cid.rsplit(".", 1)[-1].lower()
            if surface and surface in passage_focus_query(query).lower():
                boost -= 8
    if intent == "grammar":
        if cid.startswith("ru.grammar."):
            boost += 14
        elif cid.startswith(("ru.dialog.clarify.", "ru.dialog.honest.")):
            boost += 20 if not _has_inline_check_text(query) else -12
        elif cid.startswith("ru.dialog.explain"):
            boost += 8
        elif cid.startswith("ru.dialog.greeting"):
            boost -= 10
    return boost


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


def route_kb_read(
    query: str,
    bundle: dict[str, Any] | None,
    *,
    store_dir: Any | None = None,
    state: dict[str, Any] | None = None,
) -> QueryRead:
    """Surface hints → KB match → tract competition intent (ADR-0052)."""
    hints = _concept_hints_from_surface(query)
    read = QueryRead(
        intent="general",
        locales=detect_query_locales(query),
        stick_counts=parse_stick_runs(query),
        math_ops=parse_math_ops(query),
        concept_hints=hints,
    )
    if not bundle or not (bundle.get("claims") or []):
        intent, _ = compete_tract_intent(query, bundle, store_dir=store_dir, state=state)
        read.intent = intent
        return read

    hits = _filter_claim_hits(query, _match_claims(query, bundle, concept_ids=None))
    by_cid: dict[str, dict[str, Any]] = {
        str(c.get("concept_id") or ""): c for c in (bundle.get("claims") or []) if c.get("concept_id")
    }
    for hint in hints:
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
    prelim: list[tuple[dict[str, Any], int]] = []
    for claim, score in hits:
        cid = str(claim.get("concept_id") or "")
        if cid in seen:
            continue
        seen.add(cid)
        prelim.append((claim, score))
    prelim.sort(key=lambda x: x[1], reverse=True)
    geo = _geometry_honest_boosts(query, prelim)
    if geo:
        boosted: list[tuple[dict[str, Any], int]] = []
        for claim, score in prelim:
            cid = str(claim.get("concept_id") or "")
            for prefix, delta in geo.items():
                if cid.startswith(prefix):
                    score += delta
            boosted.append((claim, score))
        prelim = sorted(boosted, key=lambda x: x[1], reverse=True)
    intent, ranked = compete_tract_intent(query, bundle, kb_hits=prelim, store_dir=store_dir, state=state)
    read.intent = intent
    read.tract_ranked = ranked
    merged: list[tuple[dict[str, Any], int]] = []
    for claim, score in prelim:
        cid = str(claim.get("concept_id") or "")
        merged.append(
            (
                claim,
                score + _intent_boost_for_claim(cid, intent=intent, query=query, concept_hints=hints),
            )
        )
    merged.sort(key=lambda x: x[1], reverse=True)
    read.kb_hits = merged[:6]
    return read
