#!/usr/bin/env python3
"""Shared partner dialogue cues — affect + social zones (ADR-0061)."""

from __future__ import annotations

import re


def partner_text_lower(partner_text: str) -> str:
    return (partner_text or "").strip().lower()


def partner_says_thanks(partner_text: str) -> bool:
    return bool(re.search(r"\b(спасибо|благодар)\b", partner_text_lower(partner_text)))


def partner_repair_invite(partner_text: str) -> bool:
    pt = partner_text_lower(partner_text)
    return bool(re.search(r"\b(прости|извини)\b", pt) and re.search(r"(неожидан|странн|молч)", pt))


def partner_greeting(partner_text: str) -> bool:
    return bool(re.search(r"\b(привет|здравств)\b", partner_text_lower(partner_text)))


def infer_partner_life_event_name(partner_text: str, *, query_intent: str = "") -> str | None:
    """Partner-only life event id (affect zone vocabulary)."""
    _ = query_intent
    if partner_repair_invite(partner_text):
        return "partner_repair_invite"
    if partner_says_thanks(partner_text):
        return "partner_trust"
    if partner_greeting(partner_text):
        return "partner_greeting"
    return None


def apply_partner_trust_cue(state: dict, partner_text: str) -> bool:
    """Bump social zone trust when partner thanks — single source for regex."""
    if not partner_says_thanks(partner_text):
        return False
    bump_partner_trust(state)
    return True


def bump_partner_trust(state: dict, *, delta: float = 0.08) -> float:
    from casa.prisms.intelligence.social import ensure_social_zone

    zone = ensure_social_zone(state)
    trust = min(1.0, float(zone.get("partner_trust") or 0.5) + float(delta))
    zone["partner_trust"] = trust
    return trust
