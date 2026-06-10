"""Bind block reweight orchestration — intent + partner + zone deltas."""

from __future__ import annotations

from typing import Any

from casa.domain.dialogue_bind.blocks import is_journal_bootstrap_text, is_wake_journal_text
from casa.domain.dialogue_bind.intent_scoring import (
    intent_affinity_delta,
    kb_hit_allowed,
    text_passage_overlap,
)
from casa.domain.dialogue_bind.partner_scoring import (
    dialog_query_position_boost,
    kb_reply_present,
    max_field_overlap_for_prefix,
    partner_dialog_bind_overlap,
    partner_field_overlap,
    partner_quote_from_block,
    partner_self_label,
    partner_speech_turn,
    social_dialog_slot_allowed,
)

__all__ = [
    "intent_affinity_delta",
    "kb_hit_allowed",
    "kb_reply_present",
    "partner_dialog_bind_overlap",
    "partner_quote_from_block",
    "partner_self_label",
    "partner_speech_turn",
    "reweight_blocks_for_reply",
    "social_dialog_slot_allowed",
    "text_passage_overlap",
]


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
    from casa.prisms.memory.concept_layer import discourse_concept_id

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

    max_affect_field_ov = 0
    max_self_field_ov = 0
    max_cap_field_ov = 0
    if intent == "social":
        max_affect_field_ov = max_field_overlap_for_prefix(query, blocks, "ru.dialog.affect")
        max_self_field_ov = max_field_overlap_for_prefix(query, blocks, "ru.dialog.self")
        max_cap_field_ov = max_field_overlap_for_prefix(query, blocks, "ru.dialog.capabilities")

    for b in blocks:
        cid = str(b.get("concept_id") or "")
        disc = discourse_concept_id(b)
        text = str(b.get("text") or "")
        score = int(b.get("score") or 0)

        score += intent_affinity_delta(disc, intent=intent)
        slots = b.get("slots") if isinstance(b.get("slots"), dict) else {}
        for hint in concept_hints or []:
            if disc == hint or disc.startswith(f"{hint}.") or hint.startswith(disc):
                score += 24
            elif disc.startswith("ru.dialog.") and hint.startswith("lang.word."):
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
        if intent == "social" and disc.startswith("ru.dialog.how_are_you"):
            score = 0

        if intent == "social" and disc.startswith("ru.dialog.self"):
            if not any(h.startswith("ru.dialog.self") for h in (concept_hints or [])):
                if partner_field_overlap(query, b) < 8:
                    score -= 44

        if intent == "social":
            field_ov = partner_field_overlap(query, b)
            if field_ov >= 8 and disc.startswith("ru.dialog.affect"):
                score += min(28, field_ov * 2)
            if field_ov >= 8 and disc.startswith("ru.dialog.self"):
                score += min(28, field_ov * 2)
                if cid == "concept.agent.self":
                    score += 8
            if field_ov >= 8 and disc.startswith("ru.dialog.capabilities"):
                score += min(32, field_ov * 2)
            if max_affect_field_ov >= 8 and disc.startswith(
                ("ru.dialog.greeting", "ru.dialog.capabilities")
            ):
                score -= min(28, max_affect_field_ov * 2)
            if max_self_field_ov >= 8 and disc.startswith(("ru.dialog.greeting", "ru.dialog.affect")):
                score -= min(36, max_self_field_ov * 2)
            if max_cap_field_ov >= 8 and disc.startswith(
                ("ru.dialog.greeting", "ru.dialog.affect", "ru.dialog.self")
            ):
                score -= min(34, max_cap_field_ov * 2)

        if intent == "social" and any(h.startswith("ru.dialog.affect") for h in (concept_hints or [])):
            if disc.startswith("ru.dialog.affect"):
                score += 20
            if cid.startswith("ru.dialog.honest."):
                score += 12
            if cid.startswith(("ru.dialog.self", "ru.dialog.capabilities", "ru.dialog.how_are_you")):
                score -= 18

        if intent == "social" and any(h.startswith("ru.dialog.self") for h in (concept_hints or [])):
            if disc.startswith("ru.dialog.self") or cid == "concept.agent.self":
                score += 20

        if intent == "social" and any(
            h.startswith("ru.dialog.capabilities") for h in (concept_hints or [])
        ):
            if disc.startswith("ru.dialog.capabilities"):
                score += 24

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

        if intent == "recall":
            if b.get("source") == "journal":
                score += 28
            if str(b.get("section") or "") in ("confirmed", "journal_echo", "passage_echo"):
                score += 12
            if cid.startswith("agent.self.journal."):
                score += 16
            if cid.startswith(("ru.dialog.greeting", "ru.dialog.thanks", "ru.dialog.farewell")):
                score = 0
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
        from casa.domain.dialogue_bind.zone_scoring import apply_intelligence_zone_block_deltas

        apply_intelligence_zone_block_deltas(
            blocks, state, concept_hints=concept_hints, intent=intent
        )
        try:
            from casa.prisms.defense import apply_defense_bind_deltas

            apply_defense_bind_deltas(
                blocks,
                query,
                intent=intent,
                state=state,
                concept_hints=concept_hints,
            )
        except ImportError:
            pass

    blocks[:] = [b for b in blocks if int(b.get("score") or 0) > 0]
    blocks.sort(key=lambda row: int(row.get("score") or 0), reverse=True)
