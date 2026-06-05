#!/usr/bin/env python3
"""Kolb relink on macro tick — agent decides after surprise + self-verify (ADR-0034)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from casa.domain.edge_relink import RelinkResult, relink_vis_lex_bridge
from casa.prisms.control.fpn_state import WorkingMemory
from casa.prisms.control.tick import ControlExtensions
from casa.prisms.memory.meta_concept_aliases import canonical_lex_concept_id
from casa.prisms.shared.store_persist import mark_runtime_dirty, save_runtime_state
from casa.prisms.visual.bridge_math import vis_frame_concept_id
from casa.prisms.visual.vis_frames import FrameKind, parse_frame_ref


@dataclass(frozen=True, slots=True)
class KolbRelinkProposal:
    frame_id: str
    old_lex: str
    new_lex: str
    gate: str
    reason: str


def _session_raw(store_dir: Path) -> dict[str, Any]:
    path = store_dir / "agent_session.json"
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def agent_wants_kolb(store_dir: Path) -> bool:
    """self_drive.want_kolb in agent_session — agent asked for Kolb pass."""
    drive = _session_raw(store_dir).get("self_drive")
    return bool(isinstance(drive, dict) and drive.get("want_kolb"))


def _lang_concepts_from_blob(text: str) -> list[str]:
    if not text:
        return []
    found = re.findall(r"(?:lang\.word\.[a-z0-9]+|lang\.meta\.[a-zA-Z0-9_.]+)", text)
    out: list[str] = []
    for cid in found:
        canon = canonical_lex_concept_id(cid)
        if canon not in out:
            out.append(canon)
    return out


def _frame_id_from_context(
    *,
    wm: WorkingMemory,
    hippo_ep: dict[str, Any] | None,
    cue: str,
) -> str | None:
    focus = (wm.step_focus or "").strip()
    ref = parse_frame_ref(focus)
    if ref is not None and ref.kind != FrameKind.UNKNOWN:
        return ref.frame_id
    if focus.startswith("vis.lum.frame."):
        return focus.replace("vis.lum.frame.", "", 1)
    if hippo_ep:
        ep_cid = str(hippo_ep.get("concept_id") or "")
        if ep_cid.startswith("vis.lum.frame."):
            return ep_cid.replace("vis.lum.frame.", "", 1)
    ref = parse_frame_ref(cue)
    if ref is not None and ref.kind != FrameKind.UNKNOWN:
        return ref.frame_id
    return None


def propose_vis_lex_relink(
    *,
    wm: WorkingMemory,
    control: ControlExtensions,
    hippo_ep: dict[str, Any] | None,
    cue: str = "",
) -> KolbRelinkProposal | None:
    """Agent-side hypothesis: wrong vis↔lex binding → retarget after mismatch."""
    frame_id = _frame_id_from_context(wm=wm, hippo_ep=hippo_ep, cue=cue)
    if not frame_id:
        return None

    predicted: list[str] = []
    observed: list[str] = []
    if hippo_ep and str(hippo_ep.get("structure_tag") or "") == "predict_mismatch":
        predicted = _lang_concepts_from_blob(str(hippo_ep.get("surface_attempt") or ""))
        observed = _lang_concepts_from_blob(str(hippo_ep.get("correct") or ""))
    if not observed:
        observed = [
            canonical_lex_concept_id(c)
            for c in control.surprise
            if str(c).startswith(("lang.word.", "lang.meta."))
        ]
    if not predicted:
        predicted = [
            canonical_lex_concept_id(c)
            for c in control.predicted
            if str(c).startswith(("lang.word.", "lang.meta."))
        ]

    new_lex = ""
    old_lex = ""
    reason = ""

    if len(observed) == 1:
        new_lex = observed[0]
        if predicted:
            old_lex = predicted[0]
        reason = "surprise_single_lex_target"
    elif len(observed) >= 2 and predicted:
        # Ambiguous leaders — agent picks observed top if predicted disagrees
        new_lex = observed[0]
        old_lex = predicted[0]
        if new_lex == old_lex:
            return None
        reason = "ambiguous_lex_leaders"

    if not new_lex or not old_lex or new_lex == old_lex:
        return None
    if not new_lex.startswith("lang.word."):
        return None

    vis_cid = vis_frame_concept_id(frame_id)
    return KolbRelinkProposal(
        frame_id=frame_id,
        old_lex=old_lex,
        new_lex=new_lex,
        gate="kolb:tick_self_verify",
        reason=reason,
    )


def _self_verify_vis_lex(
    state: dict,
    *,
    frame_id: str,
    expect_lex: str,
    min_votes: int = 2,
) -> bool:
    """Second pass: novel/stable leaders must confirm new lex binding."""
    from casa.prisms.visual.analytic_read import leaders_at_max
    from casa.prisms.visual.bridge_lex import predict_lex_for_vis_cue

    preds = predict_lex_for_vis_cue(state, frame_id, top_k=8)
    top, leaders = leaders_at_max(preds)
    expect = canonical_lex_concept_id(expect_lex)
    return bool(leaders) and leaders == [expect] and top >= min_votes


def maybe_kolb_relink_tick(
    store_dir: Path,
    state: dict,
    *,
    wm: WorkingMemory,
    control: ControlExtensions,
    hippo_ep: dict[str, Any] | None = None,
    cue: str = "",
    min_surprise_value: float = 0.4,
    persist: bool = False,
) -> dict[str, Any] | None:
    """Life hook: after surprise, agent may relink vis↔lex if self-verify passes."""
    if not control.surprise and not hippo_ep:
        return None
    if control.value < min_surprise_value and not agent_wants_kolb(store_dir):
        return None

    proposal = propose_vis_lex_relink(wm=wm, control=control, hippo_ep=hippo_ep, cue=cue)
    if proposal is None:
        return None

    if not _self_verify_vis_lex(state, frame_id=proposal.frame_id, expect_lex=proposal.new_lex):
        return {
            "skipped": True,
            "reason": "self_verify_failed",
            "proposal": {
                "frame_id": proposal.frame_id,
                "old_lex": proposal.old_lex,
                "new_lex": proposal.new_lex,
                "reason": proposal.reason,
            },
        }

    result: RelinkResult = relink_vis_lex_bridge(
        state,
        frame_id=proposal.frame_id,
        old_lex_cid=proposal.old_lex,
        new_lex_cid=proposal.new_lex,
        gate=proposal.gate,
        old_relation="co_occurs",
        new_relation="denotes",
    )
    if persist:
        mark_runtime_dirty(state)
        save_runtime_state(store_dir, state)

    return {
        "gate": proposal.gate,
        "reason": proposal.reason,
        "frame_id": proposal.frame_id,
        "old_lex": proposal.old_lex,
        "new_lex": proposal.new_lex,
        "weakened": result.weakened,
        "minted": result.minted,
        "episode_id": result.episode_id,
        "want_kolb": agent_wants_kolb(store_dir),
    }
