"""FieldBus domain events (CASA-ADR-0012 §2.1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class FieldVersionDriftEvent:
    store_id: str
    old_fv: int
    new_fv: int
    stale_count: int
    stale_lattice_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ConsolidatePhaseEvent:
    store_id: str
    phase: str
    field_version: int
    shards_trained: int = 0
    detail: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class TrainCompleteEvent:
    store_id: str
    lattice_id: str
    field_version: int
    model_path: str | None = None


@dataclass(frozen=True, slots=True)
class ImpulseSummaryEvent:
    """Post-efferent impulse summary (CASA-ADR-0080)."""

    store_id: str
    tick_id: int
    impulse_id: str
    channel: str
    outcome: str
    summary: dict[str, Any] | None = None
