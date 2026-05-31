#!/usr/bin/env python3
"""Experience replay buffer for teacher corrections (anti-forgetting).

run_sleep consolidates a hippo episode once and prunes it, so an old
correction is never re-presented. Without rehearsal a later flood of
listen/ingest dilutes the strengthened concept and the agent quietly
forgets a fix it once "understood" (see understanding-contract-v0,
CASA-ADR-0009).

This module keeps a durable, lattice-agnostic record of consolidated
corrections and samples a small, spaced batch to re-inject as fresh
episodes before the next sleep. Pure functions operate on plain dicts;
the optional CLI wires them to a real field_state.json.

Schema of a buffer record (stored under state.consolidation.replay_buffer):

    {
      "episode_id": str,            # stable id -> idempotent archiving
      "kind": "surface" | "rule",
      "cue": str,
      "correct": str,
      "attempt": str | None,
      "lattice_id": str | None,
      "concept_id": str | None,
      "rule_id": str | None,
      "rule_hint": str | None,
      "correction_kind": str | None,
      "scene": str | None,
      "value": float,              # limbic/value tag -> priority weight (CASA-ADR-0010)
      "first_archived_tick": int,
      "last_replayed_tick": int | None,
      "replays": int,
    }
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

# correction_kind values that must never be auto-replayed: replaying them
# would re-assert a lemma the teacher deliberately did NOT commit (oracle on a
# short prefix) — the anti-pattern called out in teacher-correction-protocol-v0.
PENDING_CORRECTION_KINDS = frozenset({"wait_prefix", "lexical_ask"})
# episode kinds that strengthen a memory shelf on sleep and are safe to rehearse.
REPLAYABLE_KINDS = frozenset({"surface", "rule"})


def eligible_for_replay(record: dict) -> bool:
    """A correction is rehearsable only if sleep would strengthen a shelf for it.

    Excludes pending asks/hints and scene-less lexical corrections, mirroring the
    teacher-correction protocol: no lemma strengthen without commitment + scene.
    """
    if record.get("pending"):
        return False
    if record.get("kind") not in REPLAYABLE_KINDS:
        return False
    if record.get("correction_kind") in PENDING_CORRECTION_KINDS:
        return False
    if not (record.get("correct") or "").strip():
        return False
    if record.get("kind") == "rule":
        return bool(record.get("rule_id"))
    # lexical surface corrections require a scene to be a legitimate target
    if record.get("correction_kind") == "ortho_surface" and not (record.get("scene") or "").strip():
        # ortho fix on a committed word is fine without an explicit scene field;
        # only block when the source itself is ambiguous lexical.
        return True
    return True


def _record_from_merged(item: dict, *, now_tick: int) -> dict:
    """Build a durable record from a run_sleep merged item."""
    return {
        "episode_id": str(item.get("episode_id") or ""),
        "kind": str(item.get("kind") or "surface"),
        "cue": (item.get("cue") or "").strip(),
        "correct": (item.get("correct") or "").strip(),
        "attempt": (item.get("attempt") or None),
        "lattice_id": item.get("lattice_id"),
        "concept_id": item.get("concept_id"),
        "rule_id": item.get("rule_id"),
        "rule_hint": item.get("rule_hint"),
        "correction_kind": item.get("correction_kind"),
        "scene": item.get("scene"),
        "value": float(item.get("value") or 0.0),
        "first_archived_tick": int(now_tick),
        "last_replayed_tick": None,
        "replays": 0,
    }


def archive_records(buffer: list[dict], merged_items: list[dict], *, now_tick: int) -> list[dict]:
    """Append merged sleep items into the buffer, idempotent by episode_id.

    Returns the same list (mutated) for convenience.
    """
    known = {r.get("episode_id") for r in buffer if r.get("episode_id")}
    for item in merged_items or []:
        ep_id = str(item.get("episode_id") or "")
        if not ep_id or ep_id in known:
            continue
        rec = _record_from_merged(item, now_tick=now_tick)
        if not eligible_for_replay(rec):
            continue
        buffer.append(rec)
        known.add(ep_id)
    return buffer


def _staleness(record: dict, *, now_tick: int) -> int:
    last_seen = record.get("last_replayed_tick")
    if last_seen is None:
        last_seen = record.get("first_archived_tick") or 0
    return int(now_tick) - int(last_seen)


def _priority(record: dict, *, now_tick: int, value_weight: float) -> float:
    """staleness + value*w. With value_weight=0 this is plain staleness (default)."""
    return _staleness(record, now_tick=now_tick) + value_weight * float(record.get("value") or 0.0)


def prioritize(buffer: list[dict], *, now_tick: int, value_weight: float = 0.0) -> list[dict]:
    """Order eligible records by replay priority (most-forgotten / most-valued first).

    Deterministic key: larger (staleness + value*weight) first, then fewer prior
    replays, then older first_archived, then episode_id for stability.
    value_weight defaults to 0.0 -> pure recency (backward compatible).
    """
    eligible = [r for r in buffer if eligible_for_replay(r)]
    return sorted(
        eligible,
        key=lambda r: (
            -_priority(r, now_tick=now_tick, value_weight=value_weight),
            int(r.get("replays") or 0),
            int(r.get("first_archived_tick") or 0),
            str(r.get("episode_id") or ""),
        ),
    )


def sample(buffer: list[dict], k: int, *, now_tick: int, value_weight: float = 0.0) -> list[dict]:
    """Top-k spaced rehearsal batch. Does not mutate the buffer."""
    if k <= 0:
        return []
    return prioritize(buffer, now_tick=now_tick, value_weight=value_weight)[:k]


def tag_value(buffer: list[dict], episode_id: str, value: float) -> None:
    """Set the limbic value tag for a record (CASA-ADR-0010 lattice_value brick)."""
    for rec in buffer:
        if rec.get("episode_id") == episode_id:
            rec["value"] = float(value)
            return


def mark_replayed(buffer: list[dict], episode_ids: list[str], *, now_tick: int) -> None:
    """Record that the given episodes were re-presented at now_tick."""
    targets = set(episode_ids)
    for rec in buffer:
        if rec.get("episode_id") in targets:
            rec["last_replayed_tick"] = int(now_tick)
            rec["replays"] = int(rec.get("replays") or 0) + 1


def to_replay_episode_kwargs(record: dict) -> dict:
    """Translate a buffer record into kwargs for append_episode / append_rule_episode."""
    if record.get("kind") == "rule":
        return {
            "kind": "rule",
            "word": record.get("cue") or "",
            "attempt": record.get("attempt") or record.get("correct") or "",
            "correct": record.get("correct") or "",
            "rule_id": record.get("rule_id") or "",
            "rule_hint": record.get("rule_hint") or "",
        }
    return {
        "kind": "surface",
        "cue": record.get("cue") or "",
        "surface_attempt": record.get("attempt") or record.get("correct") or "",
        "correct": record.get("correct") or "",
        "lattice_id": record.get("lattice_id") or "L1_syllable",
        "concept_id": record.get("concept_id"),
        "scene": record.get("scene") or "",
        "correction_kind": record.get("correction_kind"),
    }


def get_buffer(state: dict) -> list[dict]:
    cons = state.setdefault("consolidation", {})
    buf = cons.get("replay_buffer")
    if not isinstance(buf, list):
        buf = []
        cons["replay_buffer"] = buf
    return buf


def last_sleep_items(state: dict) -> list[dict]:
    last = ((state.get("consolidation") or {}).get("last_sleep") or {}).get("items") or []
    return list(last)


def _now_tick(state: dict) -> int:
    return int((state.get("consolidation") or {}).get("last_sleep_tick") or state.get("field_version") or 0)


def _cli_apply(state: dict, batch: list[dict]) -> int:
    """Re-inject sampled records as fresh episodes. Imports are lazy on purpose."""
    from sss_cylinders_v0 import append_episode, append_rule_episode  # type: ignore

    applied = 0
    for rec in batch:
        kwargs = to_replay_episode_kwargs(rec)
        if kwargs.pop("kind") == "rule":
            append_rule_episode(
                state,
                word=kwargs["word"],
                attempt=kwargs["attempt"],
                correct=kwargs["correct"],
                rule_id=kwargs["rule_id"],
                rule_hint=kwargs["rule_hint"],
            )
        else:
            append_episode(
                state,
                cue=kwargs["cue"],
                surface_attempt=kwargs["surface_attempt"],
                correct=kwargs["correct"],
                lattice_id=kwargs["lattice_id"],
                concept_id=kwargs["concept_id"],
                scene=kwargs["scene"],
                correction_kind=kwargs["correction_kind"],
            )
        applied += 1
    return applied


def main() -> int:
    p = argparse.ArgumentParser(description="CASA correction replay buffer")
    p.add_argument("--state", required=True, type=Path, help="field_state.json")
    p.add_argument("--archive", action="store_true", help="pull last_sleep items into the buffer")
    p.add_argument("--sample", type=int, default=5, help="size of the rehearsal batch to show")
    p.add_argument("--value-weight", type=float, default=0.0, help="weight of value tag in priority (ADR-0010)")
    p.add_argument("--apply", action="store_true", help="re-inject sampled records as fresh episodes")
    args = p.parse_args()

    from field_write import load_field_state, save_field_state  # type: ignore

    state = load_field_state(args.state)
    now = _now_tick(state)
    buffer = get_buffer(state)

    if args.archive:
        archive_records(buffer, last_sleep_items(state), now_tick=now)

    batch = sample(buffer, args.sample, now_tick=now, value_weight=args.value_weight)
    dirty = bool(args.archive)

    if args.apply and batch:
        _cli_apply(state, batch)
        mark_replayed(buffer, [r["episode_id"] for r in batch], now_tick=now)
        dirty = True

    report = {
        "now_tick": now,
        "buffer_size": len(buffer),
        "eligible": len(prioritize(buffer, now_tick=now, value_weight=args.value_weight)),
        "sampled": [
            {"episode_id": r["episode_id"], "kind": r["kind"], "cue": r["cue"], "correct": r["correct"]}
            for r in batch
        ],
        "applied": bool(args.apply and batch),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if dirty:
        save_field_state(args.state, state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
