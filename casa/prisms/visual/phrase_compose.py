"""Phrase compose P1 (ADR-0033): per-word analytic read + slot bind + agreement."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

_DEFAULT_EVENTS = (
    Path(__file__).resolve().parents[3]
    / "lessons"
    / "literacy-cards"
    / "data"
    / "literacy"
    / "phrase-events-ru-pilot-v1.json"
)


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s.strip())


def load_phrase_events(path: Path | str | None = None) -> list[dict[str, Any]]:
    p = Path(path) if path else _DEFAULT_EVENTS
    doc = json.loads(p.read_text(encoding="utf-8"))
    return list(doc.get("entries") or [])


def phrase_probe_frame_id(slug: str) -> str:
    """Novel per-word crop frame inside a phrase probe (not corpus id)."""
    return f"phrase-probe-{slug}-sans"


def analytic_entry_from_word(word: dict[str, Any]) -> dict[str, Any] | None:
    """Corpus + syllabify entry for a phrase event word spec."""
    from casa.prisms.visual.corpus_lexicon import analytic_entry_from_corpus

    slug = str(word.get("slug") or "").strip()
    if slug:
        ent = analytic_entry_from_corpus(slug=slug)
        if ent:
            return ent
    surface = str(word.get("surface") or "").strip()
    if surface:
        ent = analytic_entry_from_corpus(surface=surface)
        if ent:
            return ent
    return None


def bind_slots(
    word_reads: list[dict[str, Any]],
    words_spec: list[dict[str, Any]],
) -> dict[str, Any]:
    """Map analytic reads to teacher roles by normalized surface."""
    by_surface: dict[str, dict[str, Any]] = {}
    for row in word_reads:
        surf = _nfc(str(row.get("surface") or "")).lower()
        if surf:
            by_surface[surf] = row

    slots: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for spec in words_spec:
        role = str(spec.get("role") or "")
        surf = _nfc(str(spec.get("surface") or "")).lower()
        read = by_surface.get(surf)
        if read is None:
            missing.append(role or surf)
            continue
        slots[role] = {
            "role": role,
            "surface": read.get("surface"),
            "word_concept_id": read.get("word_concept_id"),
            "verdict": read.get("verdict"),
            "via": read.get("via"),
        }

    return {
        "slots": slots,
        "missing_roles": missing,
        "complete": len(missing) == 0 and len(slots) == len(words_spec),
    }


def check_agreement(
    slots: dict[str, dict[str, Any]],
    agreement: list[dict[str, Any]],
) -> dict[str, Any]:
    """Pilot v0: agent+verb surfaces from reads match teacher agreement row."""
    if not agreement:
        return {"ok": True, "checked": 0, "details": []}

    agent_slot = slots.get("agent") or {}
    verb_slot = slots.get("verb") or {}
    agent_surf = _nfc(str(agent_slot.get("surface") or "")).lower()
    verb_surf = _nfc(str(verb_slot.get("surface") or "")).lower()

    details: list[dict[str, Any]] = []
    ok = True
    for row in agreement:
        exp_agent = _nfc(str(row.get("agent") or "")).lower()
        exp_verb = _nfc(str(row.get("verb") or "")).lower()
        row_ok = agent_surf == exp_agent and verb_surf == exp_verb
        if not row_ok:
            ok = False
        details.append(
            {
                "kind": row.get("kind"),
                "expected_agent": exp_agent,
                "expected_verb": exp_verb,
                "got_agent": agent_surf,
                "got_verb": verb_surf,
                "ok": row_ok,
            }
        )
    return {"ok": ok, "checked": len(agreement), "details": details}


def compose_phrase_verdict(
    word_reads: list[dict[str, Any]],
    entry: dict[str, Any],
    *,
    check_questions: bool = True,
) -> dict[str, Any]:
    """Aggregate per-word R1 reads into phrase-level gate (order ignored)."""
    from casa.prisms.visual.phrase_question import compose_question_verdict

    words_spec = list(entry.get("words") or [])
    bind = bind_slots(word_reads, words_spec)
    slots = bind["slots"]

    word_ok = all(str(r.get("verdict") or "") == "analytic_know" for r in word_reads)
    slot_ok = bool(bind["complete"])
    agr = check_agreement(slots, list(entry.get("agreement") or []))
    agreement_ok = bool(agr["ok"])

    verdict = "empty"
    if not word_reads:
        verdict = "empty"
    elif not word_ok:
        verdict = "word_fail"
    elif not slot_ok:
        verdict = "slot_fail"
    elif not agreement_ok:
        verdict = "agreement_fail"
    else:
        verdict = "phrase_know"

    question_out: dict[str, Any] | None = None
    if check_questions and verdict == "phrase_know" and entry.get("question_frames"):
        question_out = compose_question_verdict(slots, entry)
        if not question_out.get("question_know"):
            verdict = "question_fail"

    out = {
        "event_id": str(entry.get("event_id") or ""),
        "verdict": verdict,
        "word_reads": word_reads,
        "slots": slots,
        "slot_bind": bind,
        "agreement": agr,
        "phrase_know": verdict == "phrase_know",
    }
    if question_out is not None:
        out["question"] = question_out
    return out
