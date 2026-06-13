"""Dialogue efferent hooks for impulse trace (CASA-ADR-0080)."""

from __future__ import annotations

from typing import Any

from casa.domain.dialogue_bind import SubjectDialogueContext
from casa.domain.dialogue_provenance import bind_trace_ranked
from casa.nervous.channels import ImpulseChannel, ImpulseOutcome
from casa.nervous.impulse import impulse_recorder


def _zones_from_snap(zone_snap: dict[str, Any] | None, pre_zone: dict[str, Any] | None) -> list[str]:
    zones: list[str] = []
    for key in ("social", "linguistic", "emotional", "logical", "executive"):
        if isinstance(zone_snap, dict) and zone_snap.get(key):
            zones.append(key)
        elif isinstance(pre_zone, dict) and pre_zone.get(key):
            zones.append(key)
    return zones or ["social", "linguistic"]


def record_partner_dialogue_impulse(
    *,
    store_dir,
    ctx: SubjectDialogueContext,
    reply_text: str,
    boundary_turn: bool,
    disp_action: str | None,
    zone_snap: dict[str, Any] | None = None,
    pre_zone: dict[str, Any] | None = None,
    metabolic_rep: dict[str, Any] | None = None,
    soft_miss_reason: str = "",
) -> dict[str, Any] | None:
    rec = impulse_recorder()
    if not rec.is_active:
        return None
    with rec.channel(ImpulseChannel.PARTNER_DIALOGUE, store_dir=store_dir) as imp:
        imp.record_bind_ranked(bind_trace_ranked(ctx))
        if metabolic_rep and metabolic_rep.get("budget_exhausted"):
            imp.budget(
                "metabolic.compose_budget",
                zone="metabolic",
                reason="budget_exhausted",
                inputs={"compose_tokens": metabolic_rep.get("compose_tokens")},
            )
        if boundary_turn and disp_action:
            imp.suppress(
                "subject_disposition",
                zone="social",
                reason=str(disp_action),
            )
        zones = _zones_from_snap(zone_snap, pre_zone)
        text = (reply_text or "").strip()
        if text:
            summary = imp.finish(ImpulseOutcome.SPOKEN, zones_touched=zones)
        elif soft_miss_reason:
            imp.threshold("articulation", zone="linguistic", reason=soft_miss_reason)
            summary = imp.finish(ImpulseOutcome.SILENT, zones_touched=zones)
        else:
            summary = imp.finish(ImpulseOutcome.SILENT, zones_touched=zones)
        return dict(summary)
    return None


def record_idle_efferent_impulse(
    *,
    store_dir,
    kind: str,
    text: str | None,
    skipped: bool = False,
) -> dict[str, Any] | None:
    rec = impulse_recorder()
    if not rec.is_active:
        return None
    with rec.channel(ImpulseChannel.IDLE_EFFERENT, store_dir=store_dir) as imp:
        imp.route(
            "idle_initiative",
            zone="executive",
            inputs={"kind": kind},
            selected=[kind] if kind else [],
        )
        if skipped or not (text or "").strip():
            summary = imp.finish(ImpulseOutcome.SKIPPED, zones_touched=["executive"])
        else:
            summary = imp.finish(ImpulseOutcome.SPOKEN, zones_touched=["executive", "social"])
        return dict(summary)
    return None
