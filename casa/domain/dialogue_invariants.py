#!/usr/bin/env python3
"""Dialogue invariant probes — behavior gate (verify v2, Plan E partial)."""

from __future__ import annotations

from typing import Any

from casa.domain.dialogue_bind.blocks import score_text
from casa.domain.dialogue_bind.partner_scoring import partner_field_overlap
from casa.domain.partner_voice import partner_voice_invariant_violations

THRESHOLDS = {
    "field_overlap_floor": 8,
    "p3_distinct_hub_ratio": 0.5,
}


def probe_p7_adr0078_classes(reply: str, *, is_decline: bool = False) -> list[str]:
    """P7: ADR-0078 voice classes — fail if any violation id."""
    return partner_voice_invariant_violations(reply, is_decline=is_decline)


def probe_p2_partner_field_coupling(
    partner: str,
    reply: str,
    prov: dict[str, Any],
    *,
    phatic: bool = False,
) -> str | None:
    """P2: content turn should overlap partner field."""
    if phatic or not partner.strip() or not reply.strip():
        return None
    ov_reply = score_text(partner, reply, base=0)
    if ov_reply >= THRESHOLDS["field_overlap_floor"]:
        return None
    trace = prov.get("bind_trace") if isinstance(prov.get("bind_trace"), dict) else {}
    winner_phrase = str(trace.get("winner_phrase") or "")
    ov_winner = score_text(partner, winner_phrase, base=0) if winner_phrase else 0
    if ov_winner >= THRESHOLDS["field_overlap_floor"]:
        return None
    return f"P2: overlap(reply)={ov_reply} winner={ov_winner} floor={THRESHOLDS['field_overlap_floor']}"


def probe_p3_fixed_state_discriminator(rows: list[dict[str, Any]]) -> str | None:
    """P3 scaffold: same act class + different partner field → distinct bind hubs."""
    by_act: dict[str, list[str]] = {}
    for row in rows:
        act = str(row.get("speech_act") or "")
        hub = str(row.get("winner_hub") or "")
        if not act or not hub:
            continue
        by_act.setdefault(act, []).append(hub)
    for act, hubs in by_act.items():
        if len(hubs) < 2:
            continue
        distinct = len(set(hubs))
        ratio = distinct / len(hubs)
        if ratio < THRESHOLDS["p3_distinct_hub_ratio"]:
            return f"P3: act={act!r} hubs={hubs!r} distinct_ratio={ratio:.2f}"
    return None


def probe_p4_continuer_semantics(
    partner: str,
    reply: str,
    prov: dict[str, Any],
    *,
    referent_snippet: str = "",
) -> str | None:
    """P4: continuer should couple to referent field, not off-topic."""
    acts = prov.get("partner_speech_acts") or []
    if "ask_thought" not in acts and "thread_turn" not in acts:
        return None
    if not prov.get("thread_focus") and not any(
        str(b).startswith("dialog.context.") for b in (prov.get("bind_trace") or {}).values()
    ):
        if "dialog.context.focus_recent" not in str(prov.get("thread_focus")):
            focus_block = "dialog.context.focus_recent" in str(prov)
            if not focus_block and not prov.get("thread_focus"):
                return "P4: missing focus_recent / thread_focus evidence"
    if referent_snippet:
        ov_ref = score_text(referent_snippet, reply, base=0)
        ov_off = partner_field_overlap(partner, {"text": reply})
        if ov_ref < THRESHOLDS["field_overlap_floor"] and ov_off < THRESHOLDS["field_overlap_floor"]:
            return f"P4: continuer weak referent overlap={ov_ref}"
    return None


def probe_p5_anaphora_negative(
    partner_deictic: str,
    prov_deictic: dict[str, Any],
    partner_introspective: str,
    prov_introspective: dict[str, Any],
) -> str | None:
    """P5: deictic path carries referent; introspective path does not."""
    ref_d = (prov_deictic.get("thread_focus") or {}).get("referent_prop")
    ref_i = (prov_introspective.get("thread_focus") or {}).get("referent_prop")
    if partner_deictic and not ref_d:
        return "P5: deictic turn missing referent_prop"
    if ref_i and not ref_d:
        return None
    if ref_d and ref_i and ref_d == ref_i and "про это" not in partner_introspective.lower():
        return "P5: introspective turn inherited deictic referent"
    return None


def stage_gate_stage_ii(violations: list[str]) -> list[str]:
    """Merge-gate stage II — P7 required; P3 when matrix present."""
    return list(violations)
