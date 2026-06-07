"""Metabolic Zone — ATP tick budget, fatigue, sleep pressure (ADR-0064)."""

from casa.prisms.metabolic.zone import (
    ensure_metabolic_zone,
    metabolic_allows_tract,
    metabolic_begin_tick,
    metabolic_compose_budget,
    metabolic_end_tick,
    metabolic_policy,
    metabolic_should_sleep,
    metabolic_snapshot,
    spawn_metabolic_zone,
)

__all__ = [
    "ensure_metabolic_zone",
    "metabolic_allows_tract",
    "metabolic_begin_tick",
    "metabolic_compose_budget",
    "metabolic_end_tick",
    "metabolic_policy",
    "metabolic_should_sleep",
    "metabolic_snapshot",
    "spawn_metabolic_zone",
]
