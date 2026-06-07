"""Intent affinity, KB gating, and block reweighting."""

from __future__ import annotations

from typing import Any

from casa.domain.dialogue_bind.blocks import (
    is_journal_bootstrap_text,
    is_wake_journal_text,
    tokenize,
)


def kb_reply_present(kb_hits: list[tuple[dict[str, Any], int]]) -> bool:
    return any(str(c.get("concept_id") or "").startswith("ru.dialog.") for c, _ in kb_hits)


def kb_hit_allowed(cid: str, intent: str, passage_lemmas: set[str]) -> bool:
    if intent == "journal":
        if cid.startswith(("ru.dialog.honest.", "ru.dialog.explain.", "ru.meta.discourse.")):
            return True
        if cid.startswith("lang.word."):
            lemma = cid.rsplit(".", 1)[-1].lower()
            return bool(lemma and lemma in passage_lemmas)
        return False
    if intent not in ("discuss", "rewrite"):
        return True
    if cid.startswith("ru.meta.discourse."):
        return True
    if cid.startswith(("ru.dialog.honest.", "ru.dialog.explain")) and not passage_lemmas:
        return True
    if cid.startswith("lang.word."):
        lemma = cid.rsplit(".", 1)[-1].lower()
        return bool(lemma and lemma in passage_lemmas)
    return False


def text_passage_overlap(text: str, passage_lemmas: set[str], *, min_overlap: int = 2) -> bool:
    if not passage_lemmas:
        return False
    tt = set(tokenize(text))
    return len(tt & passage_lemmas) >= min_overlap


def intent_affinity_delta(cid: str, *, intent: str) -> int:
    """Score nudge from semantic_read intent — not query keyword routing."""
    if intent == "explain":
        if cid.startswith("ru.dialog.explain"):
            return 18
        if cid.startswith("lang.word."):
            return 14
        if cid.startswith(("ru.dialog.greeting", "ru.dialog.thanks", "ru.dialog.farewell")):
            return -24
        return 0
    if intent == "grammar":
        if cid.startswith("ru.grammar."):
            return 20
        if cid.startswith(("ru.dialog.clarify.", "ru.dialog.honest.")):
            return 16
        if cid.startswith("ru.dialog.explain"):
            return 8
        if cid.startswith(("ru.dialog.greeting", "ru.dialog.thanks")):
            return -16
        return 0
    if intent == "social":
        if cid.startswith(("ru.dialog.self", "ru.dialog.capabilities", "ru.dialog.affect")):
            return 12
        if cid.startswith(("ru.dialog.greeting", "ru.dialog.thanks", "ru.dialog.how_are_you")):
            return 10
        if cid.startswith("ru.dialog.explain"):
            return -10
        return 0
    if intent == "discuss":
        if cid.startswith("ru.prop."):
            return 28
        if cid.startswith("ru.meta.discourse."):
            return 10
        if cid.startswith("lang.word."):
            return 4
        if cid.startswith("ru.dialog."):
            return -28
        return 0
    if intent == "rewrite":
        if cid.startswith("ru.prop."):
            return 32
        if cid.startswith("ru.meta.discourse."):
            return 6
        if cid.startswith(("ru.dialog.greeting", "ru.dialog.thanks", "ru.dialog.farewell")):
            return 8
        if cid.startswith("lang.word."):
            return 4
        if cid.startswith("ru.dialog."):
            return -8
        return 0
    return 0


def reweight_blocks_for_reply(
    blocks: list[dict[str, Any]],
    query: str,
    *,
    kb_hits: list[tuple[dict[str, Any], int]],
    intent: str,
    concept_hints: list[str] | None = None,
    passage_lemmas: set[str] | None = None,
) -> None:
    """Emergent reply order: intent affinity + token overlap, not act templates."""
    kb_dialog = kb_reply_present(kb_hits)
    ql = query.lower()
    pt = passage_lemmas or set()
    has_focus_kb = any(
        str(c.get("concept_id") or "").startswith(("ru.dialog.", "ru.grammar.", "lang.word."))
        for c, _ in kb_hits
    )

    for b in blocks:
        cid = str(b.get("concept_id") or "")
        text = str(b.get("text") or "")
        score = int(b.get("score") or 0)

        score += intent_affinity_delta(cid, intent=intent)
        slots = b.get("slots") if isinstance(b.get("slots"), dict) else {}
        for hint in concept_hints or []:
            if cid == hint or cid.startswith(f"{hint}.") or hint.startswith(cid):
                score += 24
            elif cid.startswith("ru.dialog.") and hint.startswith("lang.word."):
                lemma = hint.rsplit(".", 1)[-1].lower()
                slot_word = str(
                    slots.get("stimulus") or slots.get("word") or slots.get("surface") or ""
                ).lower()
                if lemma and slot_word == lemma:
                    score += 22

        if cid.startswith("lang.word."):
            lemma = cid.rsplit(".", 1)[-1].lower()
            if lemma and lemma in ql and intent not in ("explain", "grammar"):
                score -= 22
        if intent == "social" and cid.startswith("ru.dialog.how_are_you"):
            for hint in concept_hints or []:
                if hint.startswith("lang.word.") and hint.rsplit(".", 1)[-1].lower() == "спасибо":
                    score -= 20
                    break

        if intent == "journal":
            if cid.startswith(("passage.sent.", "ru.meta.discourse.")):
                score += 18
            if b.get("source") == "journal" and str(b.get("section") or "") in (
                "confirmed",
                "journal_echo",
            ):
                score += 16
            if b.get("source") == "dialogue":
                score += 12
            if cid.startswith("subject."):
                score = min(score, 3)
        if intent in ("discuss", "rewrite"):
            if cid.startswith("ru.prop."):
                score += 34
            if str(b.get("section") or "") in (
                "passage",
                "passage_lattice",
                "passage_sent",
                "discourse",
            ) or (
                cid.startswith(("lang.word.", "passage.surface."))
                and cid.rsplit(".", 1)[-1].lower() in pt
            ):
                score += 26
            if cid.startswith("passage.sent."):
                score += 6
                if any(b2.get("concept_id", "").startswith("ru.prop.") for b2 in blocks):
                    score -= 20
                if intent == "rewrite" and any(
                    m in text.lower() for m in ("уважаем", "информируем вас", "настоящим сообщаем")
                ):
                    score -= 48
            if cid.startswith("passage.surface."):
                score += 8
            if cid.startswith("ru.meta.discourse."):
                score += 10
            if intent == "discuss" and cid.startswith("ru.dialog."):
                score = 0
            if intent == "rewrite" and cid.startswith(
                ("ru.dialog.greeting", "ru.dialog.thanks", "ru.dialog.farewell")
            ):
                score += 10
            if b.get("source") == "dialogue":
                score = min(score, 1)
            if b.get("source") == "journal" and not text_passage_overlap(text, pt):
                score = 0
            if cid.startswith("subject."):
                score = min(score, 2)
        if intent == "grammar":
            if cid.startswith(("ru.dialog.clarify.", "ru.dialog.honest.", "ru.grammar.")):
                score += 12
            if b.get("source") == "journal" and has_focus_kb:
                score = 0
            if cid.startswith("ru.dialog.") and not cid.startswith(("ru.dialog.clarify.", "ru.dialog.honest.")):
                score = 0

        if b.get("source") == "journal":
            if is_journal_bootstrap_text(text):
                score = min(score, 1)
            elif intent in ("discuss", "rewrite", "grammar", "explain", "general") and is_wake_journal_text(text):
                score = 0
            elif intent != "discuss" and (has_focus_kb or kb_dialog):
                score = min(score, 8)

        if cid.startswith("subject.") and intent != "discuss":
            score = min(score, 5)

        b["score"] = score

    blocks[:] = [b for b in blocks if int(b.get("score") or 0) > 0]
    blocks.sort(key=lambda row: int(row.get("score") or 0), reverse=True)
