"""Psychological defense mechanisms — ADR-0074 stack + trauma cement (0075)."""

from casa.prisms.defense.core import (
    DEFENSE_HONESTY_JSON,
    defense_snapshot,
    is_journal_repressed,
    limbic_denial_active,
    limbic_displacement_active,
    limbic_projection_active,
    limbic_rationalization_active,
    limbic_repression_active,
    limbic_sublimation_active,
)
from casa.prisms.defense.gate import (
    apply_defense_bind_deltas,
    apply_defense_tract_adjustment,
    build_defense_honesty_report,
    defense_after_life_event,
    filter_hot_recall_rows,
    mark_journal_repressed,
    write_defense_honesty_report,
)
from casa.prisms.defense.confabulation import (
    build_confabulated_row,
    inject_confabulated_recall,
    is_confabulated_row,
    limbic_confabulation_active,
)
from casa.prisms.defense.lattice import (
    list_defense_sandbox_state,
    place_defense_node,
    place_defense_rechannel_edge,
    prune_defense_scratch_lattices,
    spawn_defense_scratch_lattice,
)
from casa.prisms.defense.sandbox import (
    defense_sandbox_on_sublimation_defer,
    promote_rechannel_experiment,
    sandbox_bump_rechannel_score,
    sandbox_record_rechannel,
    try_auto_promote_rechannel_experiments,
)
from casa.prisms.defense.sublimation import defense_sublimation_prefers_defer
from casa.prisms.defense.trauma_cement import (
    apply_trauma_cement_bind_deltas,
    consolidate_trauma_cement,
    is_trauma_journal_row,
    limbic_trauma_tier_active,
    probe_trauma_cement_persistent,
    probe_trauma_fade_immunity,
)

__all__ = [
    "DEFENSE_HONESTY_JSON",
    "apply_defense_bind_deltas",
    "apply_defense_tract_adjustment",
    "apply_trauma_cement_bind_deltas",
    "build_confabulated_row",
    "build_defense_honesty_report",
    "consolidate_trauma_cement",
    "defense_after_life_event",
    "defense_snapshot",
    "defense_sandbox_on_sublimation_defer",
    "defense_sublimation_prefers_defer",
    "promote_rechannel_experiment",
    "sandbox_bump_rechannel_score",
    "sandbox_record_rechannel",
    "spawn_defense_scratch_lattice",
    "try_auto_promote_rechannel_experiments",
    "filter_hot_recall_rows",
    "inject_confabulated_recall",
    "list_defense_sandbox_state",
    "place_defense_node",
    "place_defense_rechannel_edge",
    "prune_defense_scratch_lattices",
    "is_confabulated_row",
    "is_journal_repressed",
    "is_trauma_journal_row",
    "limbic_confabulation_active",
    "limbic_denial_active",
    "limbic_displacement_active",
    "limbic_projection_active",
    "limbic_rationalization_active",
    "limbic_repression_active",
    "limbic_sublimation_active",
    "limbic_trauma_tier_active",
    "mark_journal_repressed",
    "probe_trauma_cement_persistent",
    "probe_trauma_fade_immunity",
    "write_defense_honesty_report",
]
