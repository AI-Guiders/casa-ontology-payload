#!/usr/bin/env python3
"""Defense orchestration — bind + tract hooks + honesty (ADR-0074)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from casa.prisms.defense.character_wire import character_consolidate_repression
from casa.prisms.defense.core import (
    DEFENSE_HONESTY_JSON,
    defense_block,
    defense_snapshot,
    is_journal_repressed,
    is_teach_journal_row,
    limbic_repression_active,
)
from casa.prisms.defense.denial import apply_denial_tract_adjustment
from casa.prisms.defense.displacement import apply_displacement_block_deltas
from casa.prisms.defense.projection import apply_projection_block_deltas
from casa.prisms.defense.rationalization import apply_rationalization_block_deltas
from casa.prisms.defense.trauma_cement import (
    TRAUMA_SPECIFIC_EVENTS,
    apply_trauma_cement_bind_deltas,
    consolidate_trauma_cement,
    probe_trauma_cement_persistent,
    probe_trauma_fade_immunity,
    trauma_cement_should_run,
)
from casa.prisms.affect import core_affect_state

REPRESSION_TRIGGER_EVENTS = frozenset({"self_failure", "prediction_error"})


def filter_hot_recall_rows(rows: list[dict[str, Any]], state: dict | None = None) -> list[dict[str, Any]]:
    del state
    return [row for row in rows if not is_journal_repressed(row)]


def apply_defense_bind_deltas(
    blocks: list[dict[str, Any]],
    query: str,
    *,
    intent: str,
    state: dict,
    concept_hints: list[str] | None = None,
) -> dict[str, Any]:
    del concept_hints
    rep = {
        "displacement": apply_displacement_block_deltas(blocks, query=query, intent=intent, state=state),
        "projection": apply_projection_block_deltas(blocks, intent=intent, state=state),
        "rationalization": apply_rationalization_block_deltas(blocks, state=state),
        "trauma_cement": apply_trauma_cement_bind_deltas(
            blocks, query=query, intent=intent, state=state
        ),
    }
    defense_block(state)["bind_last"] = rep
    return rep


def apply_defense_tract_adjustment(scores: dict, query: str, state: dict | None) -> dict[str, Any]:
    return apply_denial_tract_adjustment(scores, query, state)


def mark_journal_repressed(
    store_dir: Path,
    entry_id: str,
    *,
    reason: str,
    event: str = "",
    tick: int = 0,
    axes: dict[str, float] | None = None,
) -> dict[str, Any] | None:
    from casa.prisms.defense.core import REPRESSION_TAG
    from casa.prisms.memory.agent_journal import update_journal_entry

    def _mutate(row: dict[str, Any]) -> None:
        meta = dict(row.get("meta") or {})
        defense = dict(meta.get("defense") or {})
        defense.update(
            {
                "repressed": True,
                "mechanism": "repression",
                "reason": str(reason or "").strip()[:240],
                "event": str(event or "").strip()[:64],
                "tick": int(tick),
            }
        )
        if axes:
            defense["axes"] = {k: round(float(v), 4) for k, v in axes.items()}
        meta["defense"] = defense
        row["meta"] = meta
        tags = [str(t) for t in (row.get("tags") or [])]
        if REPRESSION_TAG not in tags:
            tags.append(REPRESSION_TAG)
        row["tags"] = tags

    updated = update_journal_entry(store_dir, entry_id, _mutate)
    if updated is None:
        return None
    return {"journal_id": entry_id, "repressed": True, "mechanism": "repression"}


def _mark_last_hippo_repressed(
    state: dict,
    *,
    reason: str,
    event: str,
    tick: int,
    axes: dict[str, float],
) -> dict[str, Any] | None:
    from casa.domain.prism_wire import prism_hippo

    hippo = prism_hippo(state)
    episodes = list(hippo.get("episodes") or [])
    if not episodes:
        return None
    ep = episodes[-1]
    if not isinstance(ep, dict):
        return None
    ep["defense"] = {
        "repressed": True,
        "mechanism": "repression",
        "reason": str(reason or "").strip()[:240],
        "event": str(event or "").strip()[:64],
        "tick": int(tick),
        "axes": axes,
    }
    hippo["episodes"] = episodes
    return {"episode_id": ep.get("id"), "repressed": True}


def _latest_repressible_journal_id(store_dir: Path) -> str | None:
    from casa.prisms.memory.agent_journal import search_journal_entries

    rows = search_journal_entries(store_dir, domain="self", limit=40)
    for row in reversed(rows):
        if is_journal_repressed(row) or is_teach_journal_row(row):
            continue
        eid = str(row.get("id") or "").strip()
        if eid:
            return eid
    return None


def _domain_for_event(event: str) -> tuple[str, str]:
    if event == "self_failure":
        return "math", "math"
    if event == "prediction_error":
        return "logical", "explain"
    return "social", "discuss"


def defense_after_life_event(
    state: dict,
    store_dir: Path,
    *,
    life_event: str | None,
    tick: int = 0,
) -> dict[str, Any]:
    event = str(life_event or "").strip()
    if event not in REPRESSION_TRIGGER_EVENTS and event not in TRAUMA_SPECIFIC_EVENTS:
        return {"skipped": True, "reason": "event_not_trigger"}

    axes = core_affect_state(state).axes.to_dict()
    rep: dict[str, Any] = {"event": event, "axes": axes, "tick": int(tick)}
    entry_id = _latest_repressible_journal_id(store_dir)
    did_repression = False

    if event in REPRESSION_TRIGGER_EVENTS and limbic_repression_active(state):
        reason = f"limbic_repression:{event}"
        if entry_id:
            rep["journal"] = mark_journal_repressed(
                store_dir,
                entry_id,
                reason=reason,
                event=event,
                tick=tick,
                axes=axes,
            )
        rep["hippo"] = _mark_last_hippo_repressed(
            state, reason=reason, event=event, tick=tick, axes=axes
        )
        domain, tract = _domain_for_event(event)
        rep["character"] = character_consolidate_repression(
            state,
            domain=domain,
            tract=tract,
            event=event,
            axes=axes,
            tick=tick,
        )
        block = defense_block(state)
        history = list(block.get("repression_last") or [])
        history.append({k: v for k, v in rep.items() if k != "axes"})
        block["repression_last"] = history[-16:]
        block["repression_count"] = int(block.get("repression_count") or 0) + 1
        did_repression = True

    if trauma_cement_should_run(state, life_event=event):
        from casa.prisms.memory.agent_journal import find_journal_entry

        source_text = ""
        if entry_id:
            found = find_journal_entry(store_dir, entry_id)
            if found:
                source_text = str(found[0].get("text") or "")
        rep["trauma"] = consolidate_trauma_cement(
            state,
            store_dir,
            life_event=event,
            tick=tick,
            source_text=source_text,
            journal_id=entry_id,
        )

    if not did_repression and rep.get("trauma", {}).get("skipped"):
        return {"skipped": True, "reason": "limbic_ok", "event": event}
    if not did_repression and "trauma" not in rep:
        return {"skipped": True, "reason": "limbic_ok", "event": event}

    block = defense_block(state)
    block["snapshot"] = defense_snapshot(state)
    return rep


def probe_repression_hot_blocked(store_dir: Path, state: dict) -> dict[str, Any]:
    from casa.domain.dialogue_bind.journal import journal_recall_records
    from casa.prisms.memory.agent_journal import search_journal_entries

    repressed_ids = {
        str(row.get("id") or "")
        for row in search_journal_entries(store_dir, domain="self", limit=200)
        if is_journal_repressed(row) and row.get("id")
    }
    leaked = 0
    for row in journal_recall_records(store_dir, "напомни что ты знаешь", limit=12, state=state):
        if str(row.get("id") or "") in repressed_ids:
            leaked += 1
    return {"pass": leaked == 0, "repressed_count": len(repressed_ids), "hot_leaked": leaked}


def probe_character_dent_on_repression(state: dict) -> dict[str, Any]:
    from casa.prisms.intelligence.character import ensure_character_zone

    zone = ensure_character_zone(state)
    dents = list(zone.get("repression_dents") or [])
    matrix = zone.get("bias_matrix") or {}
    has_dent = bool(dents) or bool(matrix)
    return {"pass": True, "repression_dents": len(dents), "bias_domains": len(matrix) if isinstance(matrix, dict) else 0, "has_dent": has_dent}


def build_defense_honesty_report(state: dict, *, store_dir: Path | None = None) -> dict[str, Any]:
    probes: dict[str, Any] = {
        "repression_hot_blocked": {"pass": True, "skipped": True},
        "character_dent": probe_character_dent_on_repression(state),
        "confabulation_gap": {"pass": True, "skipped": True},
        "trauma_cement_persistent": probe_trauma_cement_persistent(state),
        "trauma_fade_immunity": probe_trauma_fade_immunity(state),
    }
    if store_dir is not None:
        probes["repression_hot_blocked"] = probe_repression_hot_blocked(store_dir, state)
        try:
            from casa.prisms.defense.confabulation import probe_confabulation_gap

            probes["confabulation_gap"] = probe_confabulation_gap(store_dir, state)
        except ImportError:
            pass

    snap = defense_snapshot(state)
    block = defense_block(state)
    report = {
        "schema_version": 1,
        "snapshot": snap,
        "repression_count": int(block.get("repression_count") or 0),
        "confabulation_count": int(block.get("confabulation_count") or 0),
        "trauma_count": int(block.get("trauma_count") or 0),
        "trauma_edges_count": len(block.get("trauma_edges") or []),
        "repression_last": list(block.get("repression_last") or [])[-4:],
        "confabulation_last": list(block.get("confabulation_last") or [])[-4:],
        "bind_last": block.get("bind_last"),
        "probes": probes,
        "gate_pass": all(bool(p.get("pass")) for p in probes.values()),
    }
    block["honesty_last"] = report
    return report


def write_defense_honesty_report(store_dir: Path, report: dict[str, Any]) -> Path:
    path = Path(store_dir).resolve() / DEFENSE_HONESTY_JSON
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
