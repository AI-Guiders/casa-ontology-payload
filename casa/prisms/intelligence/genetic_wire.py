#!/usr/bin/env python3
"""Genetic zone pointer under intelligence_zones (ADR-0062 + 0061)."""

from __future__ import annotations

from typing import Any

from casa.prisms.genetic.zone import ensure_genetic_zone
from casa.prisms.genetic.passport import genome_passport
from casa.prisms.intelligence.model import intelligence_root


def wire_genetic_intelligence_zone(state: dict) -> dict[str, Any]:
    """Expose prism_agent.genetic_zone summary at intelligence_zones.genetic."""
    ensure_genetic_zone(state)
    passport = genome_passport(state)
    root = intelligence_root(state)
    block = {
        "ref": "prism_agent.genetic_zone",
        "role": "species_constants",
        "species_id": passport.get("species_id"),
        "genome_hash": passport.get("genome_hash"),
        "genome_hash_short": passport.get("genome_hash_short"),
        "immutable": passport.get("immutable"),
        "sealed_at_tick": passport.get("sealed_at_tick"),
        "valid": passport.get("valid"),
        "allele_summary": passport.get("allele_summary"),
    }
    root["genetic"] = block
    return block
