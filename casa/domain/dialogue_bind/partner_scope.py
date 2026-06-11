"""Partner-scoped bind — structural encapsulation, not post-hoc denylist (ADR-0077)."""

from __future__ import annotations

from typing import Any

from casa.domain.dialogue_bind.blocks import is_journal_bootstrap_text, is_wake_journal_text
from casa.domain.partner_voice import block_has_qualia_ontology_claim

OPERATOR_JOURNAL_TAGS = frozenset({"bootstrap", "operator", "debug"})

_PARTNER_SOCIAL_PREFIXES = (
    "ru.dialog.",
    "ru.speech_act.partner.",
    "lang.word.",
    "subject.dialog.",
    "subject.limbic.",
)


def _journal_tags(row: dict[str, Any]) -> set[str]:
    slots = row.get("slots") if isinstance(row.get("slots"), dict) else {}
    raw = slots.get("tags") or row.get("tags") or []
    if isinstance(raw, str):
        return {raw.strip().lower()} if raw.strip() else set()
    return {str(t).strip().lower() for t in raw if str(t).strip()}


def block_is_operator_facing(row: dict[str, Any]) -> bool:
    """Internal substrate material — never partner bind (not lemma denylist)."""
    cid = str(row.get("concept_id") or "")
    source = str(row.get("source") or "")
    text = str(row.get("text") or "")

    if cid.startswith(("agent.wm.", "agent.defense.", "subject.disposition")):
        return True
    if source == "wm_prism":
        return True
    if cid.startswith("subject.") and not cid.startswith(("subject.dialog.", "subject.limbic.")):
        return True
    if cid.startswith(("agent.field.", "agent.snapshot", "agent.self.journal.")):
        return True
    if source == "field" or cid.startswith("field."):
        return True
    if source == "journal":
        if _journal_tags(row) & OPERATOR_JOURNAL_TAGS:
            return True
        if is_journal_bootstrap_text(text) or is_wake_journal_text(text):
            return True
    return False


def partner_block_allowed(row: dict[str, Any], *, intent: str) -> bool:
    if block_is_operator_facing(row):
        return False
    if block_has_qualia_ontology_claim(row):
        return False

    cid = str(row.get("concept_id") or "")
    source = str(row.get("source") or "")

    if cid.startswith("math.") and intent != "math":
        return False

    if intent == "social":
        if source in ("dialogue", "speech_act", "limbic"):
            return True
        if cid.startswith(_PARTNER_SOCIAL_PREFIXES):
            return True
        if source == "journal":
            return True
        if cid.startswith("lang.word."):
            return True
        return False

    if intent == "math" and cid.startswith("math."):
        return True

    return not cid.startswith(("agent.", "wm."))


def apply_partner_bind_scope(
    blocks: list[dict[str, Any]],
    *,
    intent: str,
) -> list[dict[str, Any]]:
    """Keep only partner-audience blocks before compose."""
    return [row for row in blocks if partner_block_allowed(row, intent=intent)]
