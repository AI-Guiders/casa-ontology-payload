#!/usr/bin/env python3
"""Shared defense state, genome priors, limbic bands (ADR-0074)."""

from __future__ import annotations

from typing import Any

from casa.prisms.affect import core_affect_state

DEFENSE_HONESTY_JSON = "defense_honesty_report.json"

REPRESSION_TAG = "defense:repressed"
TEACH_TAGS = frozenset({"chat", "correction", "remember", "teach"})

THREAT_CUE_SUBSTRINGS = (
    "провал",
    "ошиб",
    "стыд",
    "боль",
    "страх",
    "вин",
    "неуда",
    "плохо",
    "стыдно",
)

DEFAULT_REPRESS_SECURITY = 0.35
DEFAULT_REPRESS_VALENCE = -0.12
DEFAULT_DENIAL_SECURITY = 0.42
DEFAULT_DENIAL_AROUSAL = 0.45
DEFAULT_SUBLIMATION_VALENCE = -0.15
DEFAULT_SUBLIMATION_AROUSAL = 0.5


def defense_block(state: dict) -> dict[str, Any]:
    try:
        from casa.prisms.intelligence.defense_zone import defense_core_block

        return defense_core_block(state)
    except ImportError:
        block = state.setdefault("defense", {})
        if not isinstance(block, dict):
            block = {}
            state["defense"] = block
        return block


def genetic_float(state: dict, path: str, default: float) -> float:
    try:
        from casa.prisms.genetic import genetic_constant

        val = genetic_constant(state, path)
        if val is not None:
            return float(val)
    except (ImportError, AttributeError, TypeError, ValueError):
        pass
    return default


def _axes(state: dict):
    return core_affect_state(state).axes


def repression_security_threshold(state: dict) -> float:
    block = defense_block(state)
    raw = block.get("repression_security_threshold")
    if raw is not None:
        return float(raw)
    return genetic_float(state, "defense_genotype.repression.security_threshold", DEFAULT_REPRESS_SECURITY)


def repression_valence_threshold(state: dict) -> float:
    block = defense_block(state)
    raw = block.get("repression_valence_threshold")
    if raw is not None:
        return float(raw)
    return genetic_float(state, "defense_genotype.repression.valence_threshold", DEFAULT_REPRESS_VALENCE)


def denial_security_threshold(state: dict) -> float:
    return genetic_float(state, "defense_genotype.denial.security_threshold", DEFAULT_DENIAL_SECURITY)


def denial_arousal_threshold(state: dict) -> float:
    return genetic_float(state, "defense_genotype.denial.arousal_threshold", DEFAULT_DENIAL_AROUSAL)


def limbic_repression_active(state: dict) -> bool:
    axes = _axes(state)
    return (
        axes.security < repression_security_threshold(state)
        and axes.valence < repression_valence_threshold(state)
    )


def limbic_denial_active(state: dict) -> bool:
    axes = _axes(state)
    return axes.security < denial_security_threshold(state) and axes.arousal > denial_arousal_threshold(state)


def limbic_projection_active(state: dict) -> bool:
    axes = _axes(state)
    return axes.valence < genetic_float(state, "defense_genotype.projection.valence_threshold", -0.08)


def limbic_rationalization_active(state: dict) -> bool:
    axes = _axes(state)
    return axes.security < genetic_float(state, "defense_genotype.rationalization.security_threshold", 0.45)


def limbic_displacement_active(state: dict) -> bool:
    return limbic_repression_active(state) or limbic_denial_active(state)


def limbic_sublimation_active(state: dict) -> bool:
    axes = _axes(state)
    return (
        axes.valence < genetic_float(state, "defense_genotype.sublimation.valence_threshold", DEFAULT_SUBLIMATION_VALENCE)
        and axes.arousal > genetic_float(state, "defense_genotype.sublimation.arousal_threshold", DEFAULT_SUBLIMATION_AROUSAL)
    )


def query_has_threat_cue(query: str) -> bool:
    ql = (query or "").lower()
    return any(cue in ql for cue in THREAT_CUE_SUBSTRINGS)


def text_has_threat_cue(text: str) -> bool:
    tl = (text or "").lower()
    return any(cue in tl for cue in THREAT_CUE_SUBSTRINGS)


def entry_defense_meta(row: dict[str, Any]) -> dict[str, Any]:
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    defense = meta.get("defense")
    return defense if isinstance(defense, dict) else {}


def is_journal_repressed(row: dict[str, Any]) -> bool:
    if entry_defense_meta(row).get("repressed"):
        return True
    tags = {str(t).lower() for t in (row.get("tags") or [])}
    return REPRESSION_TAG in tags


def is_teach_journal_row(row: dict[str, Any]) -> bool:
    tags = {str(t).lower() for t in (row.get("tags") or [])}
    return bool(tags & TEACH_TAGS)


def defense_snapshot(state: dict) -> dict[str, Any]:
    axes = _axes(state).to_dict()
    snap = {
        "axes": axes,
        "repression": limbic_repression_active(state),
        "denial": limbic_denial_active(state),
        "displacement": limbic_displacement_active(state),
        "projection": limbic_projection_active(state),
        "rationalization": limbic_rationalization_active(state),
        "sublimation": limbic_sublimation_active(state),
    }
    try:
        from casa.prisms.defense.confabulation import limbic_confabulation_active

        snap["confabulation"] = limbic_confabulation_active(state)
    except ImportError:
        snap["confabulation"] = False
    try:
        from casa.prisms.defense.trauma_cement import limbic_trauma_tier_active

        snap["trauma_tier"] = limbic_trauma_tier_active(state)
    except ImportError:
        snap["trauma_tier"] = False
    return snap
