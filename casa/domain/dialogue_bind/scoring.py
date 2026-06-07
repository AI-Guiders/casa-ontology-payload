"""Intent affinity, KB gating, and block reweighting."""

from __future__ import annotations

import re
from typing import Any

from casa.domain.dialogue_bind.blocks import (
    is_journal_bootstrap_text,
    is_wake_journal_text,
    score_text,
    tokenize,
)


def kb_reply_present(kb_hits: list[tuple[dict[str, Any], int]]) -> bool:
    return any(str(c.get("concept_id") or "").startswith("ru.dialog.") for c, _ in kb_hits)


def partner_quote_from_block(block: dict[str, Any]) -> str:
    text = str(block.get("text") or "")
    match = re.search(r"«([^»]+)»", text)
    return match.group(1).strip() if match else ""


def dialog_block_body(block: dict[str, Any]) -> str:
    slots = block.get("slots") if isinstance(block.get("slots"), dict) else {}
    body = " ".join(str(v) for v in slots.values())
    return f"{block.get('text') or ''} {body}".strip()


def dialog_query_position_boost(
    query: str,
    block: dict[str, Any],
    *,
    concept_hints: list[str] | None,
) -> int:
    """Earlier partner surface → stronger bind (discourse order emerges from field, not compose)."""
    ql = (query or "").lower()
    cid = str(block.get("concept_id") or "")
    slots = block.get("slots") if isinstance(block.get("slots"), dict) else {}
    anchors: list[int] = []

    for key in ("stimulus", "word", "surface"):
        surface = str(slots.get(key) or "").lower()
        if len(surface) >= 2 and surface in ql:
            anchors.append(ql.find(surface))

    for hint in concept_hints or []:
        if hint.startswith("ru.dialog.") and (cid == hint or cid.startswith(f"{hint}.")):
            for surface in ("как дела", "как ты", "как тебе здесь", "как тебе тут"):
                if surface in ql:
                    anchors.append(ql.find(surface))
        if hint == "ru.dialog.affect" and cid.startswith("ru.dialog.affect"):
            for surface in ("как дела", "как ты"):
                if surface in ql:
                    anchors.append(ql.find(surface))
        if hint.startswith("lang.word.") and cid.startswith("ru.dialog.greeting"):
            lemma = hint.rsplit(".", 1)[-1].lower()
            if lemma and lemma in ql:
                anchors.append(ql.find(lemma))

    if not anchors:
        return 0
    pos = min(anchors)
    span = max(len(ql), 8)
    return max(0, (span - pos) * 3)


def partner_self_label(quote: str) -> str:
    """Self-label in partner turn — later «Я X» after preamble (discourse structure)."""
    matches = list(re.finditer(r"[яЯ]\s+([А-ЯЁ][а-яё]{1,24})\b", quote))
    return matches[-1].group(1) if matches else ""


def partner_dialog_bind_overlap(quote: str, blocks: list[dict[str, Any]]) -> int:
    """Overlap partner quote with activated ru.dialog bind — situational, not lexicon lists."""
    best = 0
    for block in blocks:
        cid = str(block.get("concept_id") or "")
        if not cid.startswith("ru.dialog."):
            continue
        slots = block.get("slots") if isinstance(block.get("slots"), dict) else {}
        body = " ".join(str(v) for v in slots.values())
        text = f"{block.get('text') or ''} {body}"
        best = max(best, score_text(quote, text, base=0))
    return best


def partner_speech_turn(
    quote: str,
    *,
    intent: str,
    concept_hints: list[str] | None,
    blocks: list[dict[str, Any]],
) -> bool:
    """Partner turn is intro/teaching when tract + bind support it."""
    if intent != "social" or not quote.strip():
        return False
    if partner_self_label(quote):
        return True
    if partner_dialog_bind_overlap(quote, blocks) >= 8:
        return True
    hints = set(concept_hints or [])
    return bool(hints & {"ru.dialog.capabilities", "ru.dialog.thanks", "ru.dialog.affect"})


def social_dialog_slot_allowed(cid: str, *, concept_hints: list[str] | None) -> bool:
    """Dialog slot enters compose only when semantic_read routed the speech situation."""
    hints = set(concept_hints or [])
    if cid.startswith("ru.dialog.how_are_you"):
        return False
    if cid.startswith("ru.dialog.self"):
        return any(h.startswith("ru.dialog.self") for h in hints)
    return True


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
    state: dict | None = None,
) -> None:
    """Emergent reply order: intent affinity + token overlap, not act templates."""
    kb_dialog = kb_reply_present(kb_hits)
    ql = query.lower()
    pt = passage_lemmas or set()
    has_focus_kb = any(
        str(c.get("concept_id") or "").startswith(("ru.dialog.", "ru.grammar.", "lang.word."))
        for c, _ in kb_hits
    )

    partner_speech_query = partner_speech_turn(
        query,
        intent=intent,
        concept_hints=concept_hints,
        blocks=blocks,
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
            score = 0

        if intent == "social" and cid.startswith("ru.dialog.self"):
            if not any(h.startswith("ru.dialog.self") for h in (concept_hints or [])):
                score -= 44

        if intent == "social" and "ru.dialog.affect" in (concept_hints or []):
            if cid.startswith("ru.dialog.affect"):
                if "lang.word.привет" not in (concept_hints or []) or any(
                    m in ql for m in ("как тебе здесь", "как тебе тут")
                ):
                    score += 20
            if cid.startswith("ru.dialog.honest."):
                score += 12
            if cid.startswith(("ru.dialog.self", "ru.dialog.capabilities", "ru.dialog.how_are_you")):
                score -= 18

        if intent == "social" and cid.startswith("ru.dialog."):
            score += dialog_query_position_boost(query, b, concept_hints=concept_hints)

        if intent == "social" and b.get("source") == "dialogue":
            quote = partner_quote_from_block(b)
            if quote.strip().lower() == ql.strip():
                score += 24
            if quote and partner_speech_turn(
                quote,
                intent=intent,
                concept_hints=concept_hints,
                blocks=blocks,
            ):
                score += 36
            elif cid == "subject.dialog.partner_recent":
                score += 16
            if cid == "subject.dialog.self_recent":
                score += 6

        if intent == "social" and partner_speech_query:
            if cid.startswith("ru.dialog.thanks"):
                score += 18
            if cid.startswith("ru.dialog.capabilities"):
                score += 10

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

    if state is not None:
        from casa.prisms.intelligence.apply import (
            apply_zone_deltas_to_blocks,
            intelligence_compose_deltas,
        )

        apply_zone_deltas_to_blocks(blocks, intelligence_compose_deltas(state))

    blocks[:] = [b for b in blocks if int(b.get("score") or 0) > 0]
    blocks.sort(key=lambda row: int(row.get("score") or 0), reverse=True)
