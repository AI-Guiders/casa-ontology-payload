#!/usr/bin/env python3
"""Passage meaning graph — KB frames + journal prior (ADR-0053)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from casa.prisms.tick.passage.comprehend import passage_sentences, split_passage_query
from casa.prisms.tick.passage.priors import (
    _cues_all,
    _cues_any,
    _split_cues,
    apply_journal_prior,
    dialogue_tract_prior,
)

_MEANING_SECTIONS = frozenset({"meaning_frame", "meaning_emit"})
_OUTPUT_SLOT_PREFIXES = (
    "clause",
    "linker",
    "topic",
    "task",
    "stance",
    "side",
    "cause",
    "effect",
    "event",
    "actor",
    "constraint",
    "target_register",
    "register",
    "addressee",
    "quote",
    "item",
    "clause_for",
    "clause_against",
    "clause_stance",
    "linker_for",
    "linker_against",
    "linker_stance",
)


@dataclass
class PropositionRow:
    concept_id: str
    text: str
    slots: dict[str, str] = field(default_factory=dict)
    score: int = 30
    section: str = "meaning"


def _fact_anchors(passage: str) -> dict[str, str]:
    out: dict[str, str] = {}
    m = re.search(r"\d{1,2}:\d{2}", passage)
    if m:
        out["time_clock"] = m.group(0)
    m = re.search(
        r"\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)",
        passage,
        flags=re.IGNORECASE,
    )
    if m:
        out["time_date"] = m.group(0)
    m = re.search(r"№\s*\d+", passage)
    if m:
        out["place_number"] = m.group(0).replace(" ", "")
    loc = re.search(r"в\s+актовом\s+зале\s+школы\s*№\s*\d+", passage, flags=re.IGNORECASE)
    if loc:
        out["place"] = loc.group(0)
    elif "актов" in passage.lower():
        out["place"] = "актовый зал"
    if out.get("place"):
        out["place_norm"] = out["place"].replace("в актовом зале", "в актовый зал")
    return out


def _meaning_claims(bundle: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Frames from merged store bundle; bootstrap file only when bundle omitted in tests."""
    if bundle is None:
        return []
    return [
        c
        for c in (bundle.get("claims") or [])
        if str(c.get("section") or "") in _MEANING_SECTIONS and c.get("concept_id")
    ]


def _bootstrap_meaning_claims() -> list[dict[str, Any]]:
    """Honest routing when semantics bundle missing (tests / empty store)."""
    import json

    path = (
        Path(__file__).resolve().parents[4]
        / "agents/von-neumann/bundles/kb-lang-ru-lexicon-semantics-v1.bundle.json"
    )
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return [
                c
                for c in (raw.get("claims") or [])
                if str(c.get("section") or "") in _MEANING_SECTIONS
            ]
        except (OSError, json.JSONDecodeError):
            pass
    return []


def _output_slots(slots: dict[str, str], *, anchors: dict[str, str], question: str) -> dict[str, str]:
    out: dict[str, str] = {}
    ql = question.lower()
    for key, val in slots.items():
        if key.startswith("match_") or key in {
            "score",
            "anchors",
            "clause_template",
            "question_register_any",
            "if_passage",
            "emit_quote_clause",
            "emit_capture_as",
            "match_passage_regex",
            "requires_passage_any",
        }:
            continue
        if key in _OUTPUT_SLOT_PREFIXES or key.startswith(("clause_", "linker_")):
            out[key] = str(val)
    for k, v in anchors.items():
        out.setdefault(k, v)
    if slots.get("question_register_any") and _cues_any(ql, str(slots["question_register_any"])):
        out["register"] = str(slots.get("register") or "informal")
        if "родител" in ql:
            out["addressee"] = "родители"
    if slots.get("if_passage") and str(slots["if_passage"]).lower() not in anchors.get("passage", ""):
        pass
    template = slots.get("clause_template")
    if template:
        parts: list[str] = []
        for piece in str(template).split("|"):
            piece = piece.strip()
            if not piece:
                continue
            filled = piece
            for ak, av in {**anchors, **out}.items():
                filled = filled.replace("{" + ak + "}", av)
            if "{" not in filled and filled:
                parts.append(filled)
        if parts:
            out["clause_1"] = " ".join(parts)
    return out


def _frame_matches(
    claim: dict[str, Any],
    *,
    passage: str,
    question: str,
    matched_ids: set[str],
) -> bool:
    slots = claim.get("slots") if isinstance(claim.get("slots"), dict) else {}
    pl = passage.lower()
    ql = question.lower()
    has_passage = len(pl) >= 4
    passage_required = any(
        slots.get(k)
        for k in (
            "match_passage_all",
            "match_passage_any",
            "match_passage_quote",
            "match_passage_regex",
            "match_sentence_any",
            "requires_passage_any",
        )
    )
    if passage_required and not has_passage:
        return False

    if slots.get("requires_passage_any") and not _cues_any(pl, str(slots["requires_passage_any"])):
        return False

    if slots.get("match_passage_all") and not _cues_all(pl, str(slots["match_passage_all"])):
        return False
    if slots.get("match_passage_any") and not _cues_any(pl, str(slots["match_passage_any"])):
        return False
    if slots.get("deny_question_any") and _cues_any(ql, str(slots["deny_question_any"])):
        return False

    if slots.get("match_passage_quote") == "true" and not re.search(r"«[^»]+»", passage):
        return False
    regex = slots.get("match_passage_regex")
    if regex and not re.search(str(regex), pl, flags=re.IGNORECASE):
        return False
    sent_cues = slots.get("match_sentence_any")
    if sent_cues and not any(_cues_any(s, str(sent_cues)) for s in passage_sentences(passage)):
        return False

    question_required = any(slots.get(k) for k in ("match_question_all", "match_question_any"))
    if question_required:
        if slots.get("match_question_all") and not _cues_all(ql, str(slots["match_question_all"])):
            return False
        if slots.get("match_question_any") and not _cues_any(ql, str(slots["match_question_any"])):
            return False
    elif not passage_required:
        return False

    return True


def _emit_from_frame(
    claim: dict[str, Any],
    *,
    passage: str,
    question: str,
    anchors: dict[str, str],
) -> PropositionRow | None:
    slots = claim.get("slots") if isinstance(claim.get("slots"), dict) else {}
    cid = str(claim.get("concept_id") or "")
    text = str(claim.get("text") or cid)
    score = int(slots.get("score") or 30)

    out_slots = _output_slots(slots, anchors=anchors, question=question)
    if_passage = slots.get("if_passage")
    if if_passage and str(if_passage).lower() not in passage.lower():
        for k in list(out_slots.keys()):
            if k.startswith(("clause_", "linker_")) and k not in ("clause_1",):
                out_slots.pop(k, None)

    if slots.get("emit_quote_clause") == "true":
        for sent in passage_sentences(passage):
            quoted = re.findall(r"«([^»]+)»", sent)
            if quoted:
                q = quoted[0].rstrip(".!?")
                out_slots["quote"] = quoted[0]
                out_slots["clause_1"] = q
                break
        if "clause_1" not in out_slots:
            return None

    regex = slots.get("match_passage_regex")
    if regex and slots.get("emit_capture_as"):
        m = re.search(str(regex), passage, flags=re.IGNORECASE)
        if not m:
            return None
        cap = m.group(1) if m.lastindex else m.group(0)
        for i, key in enumerate(str(slots["emit_capture_as"]).split(",")):
            key = key.strip()
            if not key:
                continue
            val = cap if i == 0 else cap
            out_slots[key] = val
        if out_slots.get("item") and "clause_1" not in out_slots:
            out_slots["clause_1"] = out_slots["item"]

    if cid.startswith("ru.prop.fact.purchase") and out_slots.get("item"):
        text = f"Покупка: {out_slots['item']}."
    if cid.startswith("ru.prop.fact.quoted_speech") and out_slots.get("quote"):
        text = f"Реплика: {out_slots['quote']}."

    if not out_slots.get("clause_1") and not out_slots.get("clause_for"):
        if slots.get("constraint"):
            out_slots["constraint"] = str(slots["constraint"])
        elif not out_slots:
            return None

    return PropositionRow(cid, text, slots=out_slots, score=score)


def _rows_from_kb_frames(
    claims: list[dict[str, Any]],
    *,
    passage: str,
    question: str,
    intent: str,
) -> list[PropositionRow]:
    anchors = {**_fact_anchors(passage), "passage": passage.lower()}
    rows: list[PropositionRow] = []
    matched_ids: set[str] = set()

    for claim in claims:
        if str(claim.get("section") or "") != "meaning_frame":
            continue
        if not _frame_matches(claim, passage=passage, question=question, matched_ids=matched_ids):
            continue
        row = _emit_from_frame(claim, passage=passage, question=question, anchors=anchors)
        if row:
            rows.append(row)
            matched_ids.add(row.concept_id)

    for claim in claims:
        if str(claim.get("section") or "") != "meaning_emit":
            continue
        if not _frame_matches(claim, passage=passage, question=question, matched_ids=matched_ids):
            continue
        row = _emit_from_frame(claim, passage=passage, question=question, anchors=anchors)
        if row and row.concept_id not in matched_ids:
            rows.append(row)
            matched_ids.add(row.concept_id)

    if intent == "rewrite":
        for row in rows:
            if row.concept_id.startswith("ru.prop.event."):
                row.score += 8
    return rows


def extract_passage_meaning(
    query: str,
    *,
    intent: str = "general",
    bundle: dict[str, Any] | None = None,
    store_dir: Path | None = None,
) -> list[PropositionRow]:
    """Meaning graph from KB frames on field; journal prior optional."""
    passage, question = split_passage_query(query)
    focus = question or query
    claims = _meaning_claims(bundle)
    rows: list[PropositionRow] = []

    if not claims:
        return []

    if passage:
        rows.extend(_rows_from_kb_frames(claims, passage=passage, question=focus, intent=intent))
    elif focus and any(
        _cues_any(focus, str((c.get("slots") or {}).get("match_question_any") or ""))
        or _cues_all(focus, str((c.get("slots") or {}).get("match_question_all") or ""))
        for c in claims
        if str(c.get("section") or "") == "meaning_frame"
        and ((c.get("slots") or {}).get("match_question_any") or (c.get("slots") or {}).get("match_question_all"))
    ):
        rows.extend(_rows_from_kb_frames(claims, passage="", question=focus, intent=intent))

    apply_journal_prior(rows, store_dir=store_dir, query=query)

    seen: set[str] = set()
    deduped: list[PropositionRow] = []
    for row in rows:
        if row.concept_id in seen:
            continue
        seen.add(row.concept_id)
        deduped.append(row)
    deduped.sort(key=lambda r: r.score, reverse=True)
    return deduped


def proposition_bind_blocks(
    query: str,
    *,
    intent: str = "general",
    bundle: dict[str, Any] | None = None,
    store_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Convert proposition rows to subject_dialogue_bind block dicts."""
    return [
        {
            "concept_id": row.concept_id,
            "text": row.text,
            "section": row.section,
            "doc_path": "meaning",
            "score": row.score,
            "source": "meaning",
            "slots": dict(row.slots),
        }
        for row in extract_passage_meaning(
            query, intent=intent, bundle=bundle, store_dir=store_dir
        )
    ]


def proposition_tract_boost(
    rows: list[PropositionRow],
    *,
    store_dir: Path | None = None,
    query: str = "",
) -> dict[str, int]:
    """Affinity boost for tract competition from meaning activation."""
    boosts: dict[str, int] = {"discuss": 0, "rewrite": 0, "general": 0}
    for row in rows:
        cid = row.concept_id
        if cid.startswith("ru.prop.constraint.shift_register") or cid.startswith("ru.prop.event."):
            boosts["rewrite"] += min(20, row.score // 2)
        if cid.startswith(
            ("ru.prop.stance.", "ru.prop.argument.", "ru.prop.fact.", "ru.prop.task.", "ru.prop.inference.")
        ):
            boosts["discuss"] += min(18, row.score // 2)
    for tid, b in dialogue_tract_prior(store_dir, query=query).items():
        if tid in boosts:
            boosts[tid] += b
    return boosts
