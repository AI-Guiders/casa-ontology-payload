"""Dialogue efferent hooks for impulse trace (CASA-ADR-0080)."""

from __future__ import annotations

from typing import Any

from casa.domain.dialogue_bind import SubjectDialogueContext
from casa.domain.dialogue_provenance import bind_trace_ranked
from casa.nervous.channels import ImpulseChannel, ImpulseOutcome
from casa.nervous.compose_impulse import flush_compose_pending
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
        runtime = ctx.runtime_state if isinstance(getattr(ctx, "runtime_state", None), dict) else None
        meta = runtime.get("meta") if isinstance(runtime, dict) and isinstance(runtime.get("meta"), dict) else {}
        afferent = meta.get("neumann_afferent_event") if isinstance(meta, dict) else None
        if isinstance(afferent, dict):
            imp.select(
                "afferent_event",
                zone="linguistic",
                selected=["observed"],
                inputs={
                    "text": afferent.get("normalized_text"),
                    "turn_kind": afferent.get("turn_kind"),
                    "has_question_mark": afferent.get("has_question_mark"),
                    "punctuation": afferent.get("punctuation"),
                    "correction_kind": afferent.get("correction_kind"),
                },
            )
        understanding = meta.get("neumann_text_understanding") if isinstance(meta, dict) else None
        if isinstance(understanding, dict):
            imp.select(
                "text_understanding",
                zone="linguistic",
                selected=["observed"],
                inputs={
                    "relations": understanding.get("relations") or [],
                    "uncertainty": understanding.get("uncertainty") or [],
                },
            )
        material_plan = meta.get("neumann_material_plan") if isinstance(meta, dict) else None
        if isinstance(material_plan, dict):
            selected = material_plan.get("selected") if isinstance(material_plan.get("selected"), list) else []
            rejected = material_plan.get("rejected") if isinstance(material_plan.get("rejected"), list) else []
            potentials = []
            for row in (selected + rejected)[:12]:
                if not isinstance(row, dict):
                    continue
                potentials.append(
                    {
                        "id": str(row.get("candidate_id") or ""),
                        "score": int(row.get("score") or 0),
                        "reason": str(row.get("reason") or row.get("role") or ""),
                    }
                )
            imp.select(
                "material_plan",
                zone="linguistic",
                selected=[str(row.get("candidate_id") or "") for row in selected if isinstance(row, dict)],
                potentials=potentials,
                rejected_above_floor=len(rejected),
                inputs={
                    "focus": material_plan.get("focus"),
                    "relation_marker": material_plan.get("relation_marker"),
                    "renderer_mode": material_plan.get("renderer_mode"),
                },
            )
            imp.select(
                "renderer_decision",
                zone="linguistic",
                selected=[str(material_plan.get("renderer_mode") or "")],
                inputs={"reply_preview": (reply_text or "")[:120]},
            )
        imp.record_bind_ranked(bind_trace_ranked(ctx))
        flush_compose_pending(runtime, imp)
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
