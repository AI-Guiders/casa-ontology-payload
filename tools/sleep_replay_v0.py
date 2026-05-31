#!/usr/bin/env python3
"""Sleep-path wiring for correction replay (CASA-ADR-0009).

Orchestration lives here so ``replay_buffer_v0`` stays pure (no ``sss_cylinders``
imports) and ``sss_cylinders.run_sleep`` does not import the buffer inline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import lattice_value_v0 as lv
import replay_buffer_v0 as rb
from sss_cylinders_v0 import append_episode, append_rule_episode  # type: ignore


@dataclass(frozen=True, slots=True)
class SleepReplayConfig:
    """Knobs for archive + spaced rehearsal before a sleep merge."""

    replay_k: int = 0
    value_weight: float = 0.0


# Production sleep scripts opt in explicitly; library default stays off (no surprise).
PRODUCTION_SLEEP_REPLAY = SleepReplayConfig(replay_k=3, value_weight=0.0)


def apply_replay_batch(state: dict, batch: list[dict], *, bundle: dict | None = None) -> int:
    """Re-inject buffer records as fresh hippo episodes."""
    applied = 0
    for rec in batch:
        kwargs = rb.to_replay_episode_kwargs(rec)
        if kwargs.pop("kind") == "rule":
            append_rule_episode(
                state,
                word=kwargs["word"],
                attempt=kwargs["attempt"],
                correct=kwargs["correct"],
                rule_id=kwargs["rule_id"],
                rule_hint=kwargs["rule_hint"],
                bundle=bundle,
            )
        else:
            append_episode(
                state,
                cue=kwargs["cue"],
                surface_attempt=kwargs["surface_attempt"],
                correct=kwargs["correct"],
                lattice_id=kwargs["lattice_id"],
                concept_id=kwargs["concept_id"],
                bundle=bundle,
                scene=kwargs["scene"],
                correction_kind=kwargs["correction_kind"],
            )
        applied += 1
    return applied


def prepare_sleep_replay(
    state: dict,
    config: SleepReplayConfig,
    *,
    bundle: dict | None = None,
) -> dict[str, Any]:
    """Archive prior ``last_sleep`` items, optionally re-inject a rehearsal batch."""
    now_tick = int(state.get("field_version") or 0)
    buffer = rb.get_buffer(state)
    before = len(buffer)
    rb.archive_records(buffer, rb.last_sleep_items(state), now_tick=now_tick, tag_value=lv.tag_replay_record)
    archived_new = len(buffer) - before

    batch = (
        rb.sample(buffer, config.replay_k, now_tick=now_tick, value_weight=config.value_weight)
        if config.replay_k > 0
        else []
    )
    applied = apply_replay_batch(state, batch, bundle=bundle) if batch else 0
    if batch:
        rb.mark_replayed(buffer, [str(r["episode_id"]) for r in batch], now_tick=now_tick)

    return {
        "now_tick": now_tick,
        "archived_new": archived_new,
        "buffer_size": len(buffer),
        "replayed": applied,
        "replay_k": config.replay_k,
        "value_weight": config.value_weight,
        "episode_ids": [r.get("episode_id") for r in batch],
    }
