"""Canonical CASA v1 ontology-in-field defaults (PoC lab)."""

from __future__ import annotations

CANONICAL_CODEC = "v3"
CANONICAL_CONCEPT_MODE = "section"
CANONICAL_DAMAGE_MODE = "patches"
CANONICAL_REGION = "dmn_ontology"
# Exp B (2026-05-28): sweep on reference bundles @ damage 0.4
CANONICAL_THRESHOLD = 0.35
CANONICAL_MIN_VOTES = 2
# Hot path: decode stored field grid (single-copy tokens still visible)
CANONICAL_FIELD_MIN_VOTES = 1

REPO_PUBLIC = "https://github.com/AI-Guiders/casa-ontology-payload"
REPO_OPEN_PACK_REL = "Financial/software/open/casa-ontology-payload"
