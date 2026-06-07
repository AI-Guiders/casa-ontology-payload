#!/usr/bin/env python3
"""Idempotent migration — add Intelligence Zones to existing agent stores (ADR-0061).

Backward-compatible entry point; full migration lives in casa.prisms.intelligence.migrate.
"""

from __future__ import annotations

from casa.prisms.intelligence.migrate import (
    INTELLIGENCE_ZONES_VERSION,
    migrate_all_zones,
    migrate_emotional_zone,
    migrate_intelligence_zones,
)

__all__ = [
    "INTELLIGENCE_ZONES_VERSION",
    "migrate_all_zones",
    "migrate_emotional_zone",
    "migrate_intelligence_zones",
]

if __name__ == "__main__":
    from casa.prisms.intelligence.migrate import main

    raise SystemExit(main())
