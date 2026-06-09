"""Intent affinity and KB gating for bind reweight (semantic_read intent → block scores)."""

from __future__ import annotations

from typing import Any

from casa.domain.dialogue_bind.blocks import tokenize


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
    if intent == "recall":
        if cid.startswith("agent.self.journal."):
            return 32
        if cid.startswith(("ru.dialog.explain", "lang.word.")):
            return 8
        if cid.startswith(("ru.dialog.greeting", "ru.dialog.thanks", "ru.dialog.farewell")):
            return -28
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


def kb_intent_boost_for_claim(
    cid: str,
    *,
    intent: str,
    concept_hints: list[str],
    has_inline_check_text: bool,
    passage_focus_lower: str,
) -> int:
    """KB hit score nudge after tract intent is known (route_kb_read)."""
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
    if intent == "recall":
        if cid.startswith("agent.self.journal."):
            boost += 24
        elif cid.startswith("ru.dialog."):
            boost -= 14
    if intent == "social":
        if cid.startswith("ru.dialog."):
            boost += 18
        elif cid.startswith("lang.word."):
            boost += 8
            surface = cid.rsplit(".", 1)[-1].lower()
            if surface and surface in passage_focus_lower:
                boost -= 8
    if intent == "grammar":
        if cid.startswith("ru.grammar."):
            boost += 14
        elif cid.startswith(("ru.dialog.clarify.", "ru.dialog.honest.")):
            boost += 20 if not has_inline_check_text else -12
        elif cid.startswith("ru.dialog.explain"):
            boost += 8
        elif cid.startswith("ru.dialog.greeting"):
            boost -= 10
    return boost


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
